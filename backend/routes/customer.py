"""Customer endpoints: browse batches, orders, wishlist, reviews, alerts, etc."""
import random
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify, g, Response
from sqlalchemy import func

from db import db
from models import (
    JaggeryBatch, Order, OrderItem, Promotion, Warehouse,
    Wishlist, Review, PriceAlert, DeliveryCharge, AbandonedCart, User,
)
from auth import (role_required, customer_required, optional_auth, audit,
                  hash_password, verify_password)
from services import price_order
from utils.helpers import invoice_pdf, payment_slip_pdf
from utils.email_util import send_bulk, email_enabled
from config import Config


def _mask_email(email):
    try:
        name, domain = email.split("@", 1)
        return (name[0] + "***" if name else "***") + "@" + domain
    except (ValueError, AttributeError):
        return "your email"


def _pay_otp_valid(user, code):
    if not user.pay_otp_hash or not user.pay_otp_expires:
        return False
    exp = user.pay_otp_expires
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > exp:
        return False
    return verify_password(code or "", user.pay_otp_hash)


_METHOD_LABELS = {"kpay": "KPay", "wavepay": "Wave Pay", "ayapay": "AYA Pay",
                  "cbpay": "CB Pay", "yomapay": "Yoma Pay", "bank": "Bank Transfer"}
_METHOD_ORDER = ["kpay", "wavepay", "ayapay", "cbpay", "yomapay", "bank"]

_METHOD_LABELS = {"kpay": "KPay", "wavepay": "Wave Pay", "ayapay": "AYA Pay",
                  "cbpay": "CB Pay", "yomapay": "Yoma Pay", "bank": "Bank Transfer"}
_METHOD_ORDER = ["kpay", "wavepay", "ayapay", "cbpay", "yomapay", "bank"]

bp = Blueprint("customer", __name__, url_prefix="/api")


def _charge_row(name):
    """Admin-configured charge row for a location name (case/space insensitive)."""
    if not name:
        return None
    return (DeliveryCharge.query
            .filter(func.lower(DeliveryCharge.pincode) == name.strip().lower())
            .first())


def _foreign_band(fee):
    """Foreign delivery always costs between FOREIGN_FEE_MIN and FOREIGN_FEE_MAX Kyats."""
    return float(min(max(float(fee), Config.FOREIGN_FEE_MIN), Config.FOREIGN_FEE_MAX))


def _delivery_charge_for(pincode, scope=None):
    """
    Charge for the customer's chosen delivery location.

    pincode = the location picked at checkout (a Myanmar city for "local",
    a country for "foreign"). Local fees come from the admin's delivery-charge
    table, falling back to the flat default. Foreign fees depend on the country:
    the admin's row for that exact country wins, then the built-in per-country
    fee, then the admin's generic "Foreign" row — and whatever the source, a
    foreign fee is always kept inside the 20,000–50,000 Kyats band.
    """
    key = (pincode or "").strip().lower()
    foreign = (scope or "").strip().lower() == "foreign" or key in Config.FOREIGN_COUNTRY_FEES
    dc = _charge_row(pincode)
    if dc:
        fee = float(dc.charge_amount)
        return _foreign_band(fee) if foreign else fee
    if foreign:
        fee = Config.FOREIGN_COUNTRY_FEES.get(key)
        if fee is None:
            dc = _charge_row("Foreign")
            fee = float(dc.charge_amount) if dc else Config.DEFAULT_DELIVERY_FEE
        return _foreign_band(fee)
    return float(Config.DEFAULT_DELIVERY_FEE)


def _viewer_role():
    """Role of whoever is asking — 'guest' when nobody is logged in."""
    user = getattr(g, "current_user", None)
    return user.role if user else "guest"


@bp.get("/batches")
@optional_auth
def list_batches():
    """
    Public catalogue — browsable without logging in. Optional filters:
    ?grade=A&warehouse_id=1

    Guests and customers see only live products; admin/warehouse see everything.
    """
    q = JaggeryBatch.query
    grade = request.args.get("grade")
    warehouse_id = request.args.get("warehouse_id", type=int)
    if grade:
        q = q.filter_by(grade=grade.upper())
    if warehouse_id:
        q = q.filter_by(warehouse_id=warehouse_id)
    # deleted stock never shows in the catalogue (warehouse-deleted products)
    q = q.filter(JaggeryBatch.deleted_at.is_(None))
    # guests + customers only see active (live) products
    if _viewer_role() in ("guest", "customer"):
        q = q.filter_by(is_active=True)
    batches = q.order_by(JaggeryBatch.harvest_date.desc()).all()
    return jsonify([b.to_dict() for b in batches])


@bp.get("/content/<key>")
def site_content(key):
    """Public, admin-edited page copy (About Us, grade descriptions). Unsaved
    keys → {} so the frontend's built-in bilingual defaults render."""
    from models import SiteContent
    if key not in ("about", "grades"):
        return jsonify({"error": "unknown content key"}), 404
    row = db.session.get(SiteContent, key)
    return jsonify(row.data if row and row.data else {})


@bp.get("/announcements/active")
@optional_auth
def active_announcements():
    """Public announcement board — shown on all dashboards and the guest home."""
    from models import Announcement
    now = datetime.utcnow()
    rows = (Announcement.query
            .filter((Announcement.expires_at.is_(None)) | (Announcement.expires_at >= now))
            .order_by(Announcement.created_at.desc()).all())
    return jsonify([a.to_dict() for a in rows])


@bp.get("/advertisements/active")
@optional_auth
def active_advertisements():
    """Daily advertisements that are active and within their date window today."""
    from models import Advertisement
    from datetime import date
    today = date.today()
    rows = Advertisement.query.filter(
        Advertisement.is_active.is_(True),
        (Advertisement.starts_on.is_(None)) | (Advertisement.starts_on <= today),
        (Advertisement.ends_on.is_(None)) | (Advertisement.ends_on >= today),
    ).order_by(Advertisement.created_at.desc()).all()
    return jsonify([a.to_dict() for a in rows])


@bp.get("/orders/history-chart")
@customer_required
def order_history_chart():
    """Monthly order totals for the logged-in customer (Chart.js)."""
    from sqlalchemy import func
    rows = (db.session.query(func.to_char(Order.created_at, "YYYY-MM"),
                             func.coalesce(func.sum(Order.total_price), 0))
            .filter(Order.customer_id == g.current_user.id, Order.status != "cancelled")
            .group_by(func.to_char(Order.created_at, "YYYY-MM"))
            .order_by(func.to_char(Order.created_at, "YYYY-MM")).all())
    return jsonify({"labels": [r[0] for r in rows], "values": [round(float(r[1])) for r in rows]})


@bp.get("/stats/guest")
@optional_auth
def guest_stats():
    """Public shop-front counter shown to visitors: registered customer accounts."""
    return jsonify({"users": User.query.filter_by(role="customer").count()})


@bp.get("/promotions/active")
@optional_auth
def active_promotions():
    today = datetime.utcnow().date()
    promos = Promotion.query.filter(
        Promotion.is_active.is_(True),
        Promotion.start_date <= today,
        Promotion.end_date >= today,
    ).all()
    return jsonify([p.to_dict() for p in promos])


@bp.post("/orders")
@role_required("customer")
def place_order():
    """
    Body:
    {
      "delivery_address": "...",
      "preferred_date": "2026-06-20",
      "items": [{"batch_pk": 1, "qty_kg": 6}, ...]
    }
    Business rules enforced:
      - batch must exist and not be near expiry
      - stock must cover requested qty
      - promotion auto-applies on total qty
    """
    data = request.get_json(silent=True) or {}
    address = (data.get("delivery_address") or "").strip()
    pincode = (data.get("pincode") or "").strip()[:60] or None
    # local (a Myanmar city) or foreign (a country) — only used to price delivery
    scope = (data.get("delivery_scope") or "").strip().lower()
    if scope not in ("local", "foreign"):
        scope = "local"
    items = data.get("items") or []
    fulfillment = (data.get("fulfillment") or "delivery").strip().lower()
    if fulfillment not in ("delivery", "pickup"):
        fulfillment = "delivery"
    # 'cod' => pay on delivery (order stays unpaid); otherwise pay online later
    pay_choice = (data.get("payment_method") or "").strip().lower() or None
    if not address:
        return jsonify({"error": "delivery_address is required"}), 400
    if not items:
        return jsonify({"error": "at least one order item is required"}), 400

    preferred_date = None
    if data.get("preferred_date"):
        try:
            preferred_date = datetime.strptime(data["preferred_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "preferred_date must be YYYY-MM-DD"}), 400

    line_items = []
    total_qty = 0.0
    try:
        for it in items:
            batch_pk = it.get("batch_pk")
            qty = float(it.get("qty_kg", 0))
            if qty <= 0:
                return jsonify({"error": "qty_kg must be positive"}), 400

            # Lock the row so concurrent orders can't oversell the same batch
            batch = (
                JaggeryBatch.query.filter_by(id=batch_pk)
                .with_for_update()
                .first()
            )
            if not batch:
                return jsonify({"error": f"category {batch_pk} not found"}), 404
            if batch.is_expired:
                return jsonify({
                    "error": f"category {batch.batch_id} is EXPIRED and cannot be ordered"
                }), 422
            if not batch.is_active:
                return jsonify({"error": f"category {batch.batch_id} is not available"}), 422
            if float(batch.qty_kg) < qty:
                return jsonify({
                    "error": f"insufficient stock for {batch.batch_id}: "
                             f"{float(batch.qty_kg)}kg available, {qty}kg requested"
                }), 422

            unit = float(batch.price_per_kg)
            line_total = round(unit * qty)
            line_items.append({
                "batch": batch, "qty": qty, "unit": unit, "line_total": line_total
            })
            total_qty += qty

        subtotal, discount, total, promo = price_order(line_items, total_qty)
        # pickup is free; delivery uses the admin-configured per-region charge
        delivery_charge = 0.0 if fulfillment == "pickup" else _delivery_charge_for(pincode, scope)

        # permanent per-customer order number (never decreases, even if orders are deleted/cancelled)
        g.current_user.order_count = (g.current_user.order_count or 0) + 1

        # every product belongs to a warehouse — route the order straight to that
        # warehouse automatically (no admin assignment needed)
        owner_warehouse_id = line_items[0]["batch"].warehouse_id

        order = Order(
            customer_id=g.current_user.id,
            # pay-on-delivery is confirmed immediately -> waiting; online stays pending until paid
            status=("waiting" if pay_choice == "cod" else "pending"),
            assigned_warehouse_id=owner_warehouse_id,
            customer_seq=g.current_user.order_count,
            delivery_address=address,
            pincode=pincode,
            delivery_scope=scope,
            preferred_date=preferred_date,
            subtotal=subtotal,
            discount_amount=discount,
            delivery_charge=delivery_charge,
            total_price=total,
            fulfillment=fulfillment,
            payment_method="cod" if pay_choice == "cod" else None,
            payment_status="unpaid",
            promotion_id=promo.id if promo else None,
        )
        db.session.add(order)
        db.session.flush()  # get order.id

        for li in line_items:
            db.session.add(OrderItem(
                order_id=order.id,
                batch_pk=li["batch"].id,
                qty_kg=li["qty"],
                unit_price=li["unit"],
                line_total=li["line_total"],
            ))
            # decrement stock
            li["batch"].qty_kg = float(li["batch"].qty_kg) - li["qty"]

        db.session.commit()
        return jsonify({
            "message": "order placed",
            "order": order.to_dict(),
            "applied_promotion": promo.to_dict() if promo else None,
        }), 201

    except Exception as exc:  # noqa: BLE001 — convert any failure into clean rollback
        db.session.rollback()
        return jsonify({"error": f"could not place order: {exc}"}), 500


@bp.get("/orders")
@role_required("customer")
def my_orders():
    orders = (
        Order.query.filter_by(customer_id=g.current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return jsonify([o.to_dict() for o in orders])


@bp.get("/payment-methods")
@role_required("customer", "admin", "warehouse")
def customer_payment_methods():
    """Online payment providers offered to customers at checkout."""
    return jsonify([
        {"key": k, "label": _METHOD_LABELS[k], "account": Config.MERCHANT_ACCOUNTS.get(k, "")}
        for k in _METHOD_ORDER if k in Config.PAYMENT_METHODS
    ])


@bp.get("/delivery-quote")
@role_required("customer")
def delivery_quote():
    """Delivery fee for the chosen location (?pincode=Yangon&scope=local|foreign)."""
    pincode = (request.args.get("pincode") or "").strip() or None
    scope = (request.args.get("scope") or "").strip().lower() or None
    return jsonify({"pincode": pincode, "scope": scope,
                    "charge": _delivery_charge_for(pincode, scope)})


@bp.get("/delivery-locations")
@role_required("customer")
def delivery_locations():
    """
    The admin's delivery-charge table, for the checkout location dropdown.
    Checkout uses it to price each city/country the moment it is picked, so the
    fee a customer sees always matches what the admin configured.
    """
    rows = DeliveryCharge.query.order_by(DeliveryCharge.pincode).all()
    # Resolved per-country foreign fees (admin override + 20k–50k band applied),
    # so the checkout dropdown always shows exactly what the order gets charged.
    by_name = {str(r.pincode).strip().lower(): float(r.charge_amount) for r in rows}
    foreign_fees = {
        country: round(_foreign_band(by_name.get(country, fee)))
        for country, fee in Config.FOREIGN_COUNTRY_FEES.items()
    }
    generic = by_name.get("foreign", Config.DEFAULT_DELIVERY_FEE)
    return jsonify({
        "default_charge": float(Config.DEFAULT_DELIVERY_FEE),
        "locations": [{"location": r.pincode, "charge": round(float(r.charge_amount))}
                      for r in rows],
        "foreign_fees": foreign_fees,
        # catch-all for a country not in the built-in list
        "foreign_default_charge": round(_foreign_band(generic)),
    })


@bp.get("/orders/<int:order_id>")
@role_required("customer")
def get_order(order_id):
    order = Order.query.filter_by(id=order_id, customer_id=g.current_user.id).first()
    if not order:
        return jsonify({"error": "order not found"}), 404
    return jsonify(order.to_dict())


@bp.post("/orders/<int:order_id>/pay/request-otp")
@role_required("customer")
def pay_request_otp(order_id):
    """Email a 6-digit verification code the customer must enter to confirm payment."""
    order = Order.query.filter_by(id=order_id, customer_id=g.current_user.id).first()
    if not order:
        return jsonify({"error": "order not found"}), 404
    if order.payment_status == "paid":
        return jsonify({"error": "this order is already paid"}), 422

    user = g.current_user
    code = f"{random.randint(0, 999999):06d}"
    user.pay_otp_hash = hash_password(code)
    user.pay_otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.commit()

    result = send_bulk([user.email], "Your payment verification code",
                       f"Your code to confirm payment for order #{order.id} is {code}. "
                       f"It expires in 10 minutes.")
    audit("payment_otp_requested", _mask_email(user.email))
    db.session.commit()
    resp = {"sent": True, "email": _mask_email(user.email), "delivery": result.get("status")}
    if not email_enabled():
        resp["dev_code"] = code  # demo: surface the code so it's testable on screen
    return jsonify(resp)


@bp.post("/orders/<int:order_id>/pay")
@role_required("customer")
def pay_order(order_id):
    """Confirm an online payment for an order — requires the emailed OTP."""
    order = Order.query.filter_by(id=order_id, customer_id=g.current_user.id).first()
    if not order:
        return jsonify({"error": "order not found"}), 404
    if order.status == "cancelled":
        return jsonify({"error": "cancelled orders cannot be paid"}), 422
    if order.payment_status == "paid":
        return jsonify({"error": "this order is already paid"}), 422

    data = request.get_json(silent=True) or {}
    method = (data.get("method") or "").strip().lower()
    reference = (data.get("reference") or "").strip()
    phone = (data.get("phone") or "").strip()
    otp = (data.get("otp") or "").strip()
    if method not in Config.PAYMENT_METHODS:
        return jsonify({"error": "please choose a valid payment method"}), 400
    if not phone:
        return jsonify({"error": "phone number is required"}), 400
    if not reference:
        return jsonify({"error": "transaction reference is required"}), 400
    if not _pay_otp_valid(g.current_user, otp):
        return jsonify({"error": "invalid or expired verification code"}), 403

    order.payment_method = method
    order.payment_reference = reference
    order.payment_phone = phone
    order.payment_status = "paid"
    if order.status == "pending":
        order.status = "waiting"   # payment finished -> warehouse can now handle it
    g.current_user.pay_otp_hash = None      # consume the code
    g.current_user.pay_otp_expires = None
    audit("order_payment", f"order {order.id} paid via {method} ref {reference}")
    db.session.commit()
    return jsonify({"message": "payment confirmed", "order": order.to_dict()})


@bp.get("/orders/<int:order_id>/payment-slip")
@role_required("customer")
def order_payment_slip(order_id):
    """Downloadable PDF payment slip for a paid order."""
    order = Order.query.filter_by(id=order_id, customer_id=g.current_user.id).first()
    if not order:
        return jsonify({"error": "order not found"}), 404
    if order.payment_status != "paid":
        return jsonify({"error": "this order is not paid"}), 422
    d = order.to_dict()
    pairs = [
        ("Order", f"#{d.get('customer_seq')}"),
        ("Customer", d.get("customer_name") or ""),
        ("Date", order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else ""),
        ("Payment method", d.get("payment_method_label") or ""),
        ("Transaction ID", d.get("payment_reference") or ""),
        ("Paid from phone", d.get("payment_phone") or ""),
        ("Payment status", "PAID"),
    ]
    # category (product) details + the warehouse + the value of each
    item_headers = ["Category", "Warehouse", "Grade", "Qty (kg)", "Unit (Kyats)", "Value (Kyats)"]
    items = [[it["batch_id"], it.get("warehouse_name") or "-", it["grade"], f"{it['qty_kg']}",
              f"{it['unit_price']} Kyats", f"{it['line_total']} Kyats"] for it in d["items"]]
    items.append(["Subtotal", "", "", "", "", f"{d['subtotal']} Kyats"])
    if float(d.get("discount_amount") or 0) > 0:
        items.append(["Discount", "", "", "", "", f"-{d['discount_amount']} Kyats"])
    items.append(["Delivery", "", "", "", "", f"{d['delivery_charge']} Kyats"])
    pdf = payment_slip_pdf("Payment Receipt", pairs, f"{d['grand_total']} Kyats",
                           "Thank you for your purchase.", items=items, item_headers=item_headers)
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=payment_order_{order.id}.pdf"})


@bp.post("/orders/<int:order_id>/cancel")
@role_required("customer")
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, customer_id=g.current_user.id).first()
    if not order:
        return jsonify({"error": "order not found"}), 404
    if order.status not in ("pending", "waiting"):
        return jsonify({"error": "only orders not yet shipped can be cancelled"}), 422

    try:
        # restock
        for item in order.items:
            if item.batch:
                item.batch.qty_kg = float(item.batch.qty_kg) + float(item.qty_kg)
        order.status = "cancelled"
        db.session.flush()

        # re-sequence the customer's remaining (non-cancelled) orders so the order
        # numbers stay contiguous after a cancel: oldest = 1 … newest = N.
        remaining = (Order.query
                     .filter(Order.customer_id == g.current_user.id,
                             Order.status != "cancelled")
                     .order_by(Order.created_at.asc(), Order.id.asc())
                     .all())
        for idx, o in enumerate(remaining, start=1):
            o.customer_seq = idx
        g.current_user.order_count = len(remaining)

        db.session.commit()
        return jsonify({"message": "order cancelled", "order": order.to_dict()})
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return jsonify({"error": f"could not cancel: {exc}"}), 500


# ----------------------------------------------------------------- wishlist
@bp.get("/wishlist")
@customer_required
def get_wishlist():
    items = Wishlist.query.filter_by(customer_id=g.current_user.id).all()
    return jsonify([w.to_dict() for w in items])


@bp.post("/wishlist")
@customer_required
def add_wishlist():
    batch_pk = (request.get_json(silent=True) or {}).get("batch_id")
    if not db.session.get(JaggeryBatch, batch_pk):
        return jsonify({"error": "category not found"}), 404
    if Wishlist.query.filter_by(customer_id=g.current_user.id, batch_id=batch_pk).first():
        return jsonify({"message": "already in wishlist"})
    db.session.add(Wishlist(customer_id=g.current_user.id, batch_id=batch_pk))
    db.session.commit()
    return jsonify({"message": "added to wishlist"}), 201


@bp.delete("/wishlist/<int:batch_pk>")
@customer_required
def remove_wishlist(batch_pk):
    w = Wishlist.query.filter_by(customer_id=g.current_user.id, batch_id=batch_pk).first()
    if w:
        db.session.delete(w)
        db.session.commit()
    return jsonify({"message": "removed"})


# ------------------------------------------------------------ rate & review
@bp.post("/orders/<int:order_id>/review")
@customer_required
def add_review(order_id):
    order = Order.query.filter_by(id=order_id, customer_id=g.current_user.id).first()
    if not order:
        return jsonify({"error": "order not found"}), 404
    if order.status != "shipped":
        return jsonify({"error": "you can review only after the order is shipped"}), 422
    if order.review:
        return jsonify({"error": "order already reviewed"}), 409

    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    if rating not in (1, 2, 3, 4, 5):
        return jsonify({"error": "rating must be 1-5"}), 400

    review = Review(
        order_id=order.id, customer_id=g.current_user.id,
        warehouse_id=order.assigned_warehouse_id,
        rating=rating, comment=(data.get("comment") or "").strip(),
    )
    db.session.add(review)
    db.session.commit()
    return jsonify({"message": "review submitted", "review": review.to_dict()}), 201


# ----------------------------------------------------- repeat order (1-click)
@bp.post("/orders/repeat")
@customer_required
def repeat_order():
    last = (Order.query.filter_by(customer_id=g.current_user.id)
            .filter(Order.status != "cancelled")
            .order_by(Order.created_at.desc()).first())
    if not last:
        return jsonify({"error": "no previous order to repeat"}), 404

    try:
        line_items, total_qty = [], 0.0
        for it in last.items:
            batch = JaggeryBatch.query.filter_by(id=it.batch_pk).with_for_update().first()
            if not batch or batch.is_expired or not batch.is_active:
                return jsonify({"error": f"category {it.batch.batch_id if it.batch else it.batch_pk} no longer available"}), 422
            if float(batch.qty_kg) < float(it.qty_kg):
                return jsonify({"error": f"insufficient stock for {batch.batch_id}"}), 422
            unit = float(batch.price_per_kg)
            line_items.append({"batch": batch, "qty": float(it.qty_kg), "unit": unit,
                               "line_total": round(unit * float(it.qty_kg))})
            total_qty += float(it.qty_kg)

        subtotal, discount, total, promo = price_order(line_items, total_qty)
        # re-price against today's charge for the same location the last order used
        dc = _delivery_charge_for(last.pincode, last.delivery_scope)
        order = Order(customer_id=g.current_user.id, status="pending",
                      delivery_address=last.delivery_address, pincode=last.pincode,
                      delivery_scope=last.delivery_scope or "local",
                      subtotal=subtotal, discount_amount=discount, delivery_charge=dc,
                      total_price=total, promotion_id=promo.id if promo else None)
        db.session.add(order)
        db.session.flush()
        for li in line_items:
            db.session.add(OrderItem(order_id=order.id, batch_pk=li["batch"].id,
                                     qty_kg=li["qty"], unit_price=li["unit"], line_total=li["line_total"]))
            li["batch"].qty_kg = float(li["batch"].qty_kg) - li["qty"]
        db.session.commit()
        return jsonify({"message": "order repeated", "order": order.to_dict()}), 201
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


# ------------------------------------------------------------ compare batches
@bp.get("/batches/compare")
@role_required("customer", "admin", "warehouse")
def compare_batches():
    """?ids=1,2,3 — return 2-3 batches side by side."""
    ids = [int(x) for x in (request.args.get("ids") or "").split(",") if x.strip().isdigit()]
    if not (2 <= len(ids) <= 3):
        return jsonify({"error": "provide 2 or 3 category ids: ?ids=1,2"}), 400
    batches = JaggeryBatch.query.filter(JaggeryBatch.id.in_(ids)).all()
    return jsonify([b.to_dict() for b in batches])


# -------------------------------------------------------------- invoice PDF
@bp.get("/orders/<int:order_id>/invoice")
@customer_required
def download_invoice(order_id):
    order = Order.query.filter_by(id=order_id, customer_id=g.current_user.id).first()
    if not order:
        return jsonify({"error": "order not found"}), 404
    pdf = invoice_pdf(order.to_dict())
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=invoice_{order_id}.pdf"})


# ----------------------------------------------------- nearby warehouse finder
@bp.get("/warehouses/nearby")
@role_required("customer", "admin", "warehouse")
def nearby_warehouses():
    """?pincode=416001 — warehouses sorted by |pincode difference| (simple proxy)."""
    pincode = request.args.get("pincode", "")
    whs = Warehouse.query.all()
    def dist(w):
        try:
            return abs(int(w.pincode or 0) - int(pincode or 0))
        except ValueError:
            return 10 ** 9
    ordered = sorted(whs, key=dist)
    return jsonify([{**w.to_dict(), "pincode_distance": dist(w)} for w in ordered])


# --------------------------------------------------------------- price alerts
@bp.get("/price-alerts")
@customer_required
def list_price_alerts():
    alerts = PriceAlert.query.filter_by(customer_id=g.current_user.id).all()
    return jsonify([a.to_dict() for a in alerts])


@bp.post("/price-alerts")
@customer_required
def create_price_alert():
    data = request.get_json(silent=True) or {}
    batch = db.session.get(JaggeryBatch, data.get("batch_id"))
    if not batch:
        return jsonify({"error": "category not found"}), 404
    try:
        desired = float(data["desired_price"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "desired_price (number) required"}), 400
    alert = PriceAlert(customer_id=g.current_user.id, batch_id=batch.id, desired_price=desired)
    db.session.add(alert)
    db.session.commit()
    return jsonify({"message": "price alert set", "alert": alert.to_dict()}), 201


# ----------------------------------------------------------- abandoned carts
@bp.post("/cart/abandon")
@customer_required
def capture_abandoned_cart():
    """Snapshot a non-empty cart (called by the frontend on logout). Keeps one
    current snapshot per customer."""
    items = (request.get_json(silent=True) or {}).get("items") or []
    if not items:
        return jsonify({"message": "nothing to capture"})
    AbandonedCart.query.filter_by(customer_id=g.current_user.id).delete()
    db.session.add(AbandonedCart(customer_id=g.current_user.id, items_json=items))
    db.session.commit()
    return jsonify({"message": "cart snapshot saved", "items": len(items)})


# ------------------------------------------------------- warehouse ratings
@bp.get("/warehouses/ratings")
@optional_auth
def warehouse_ratings():
    """Average star rating + review count per warehouse (for the catalogue)."""
    rows = (db.session.query(Review.warehouse_id, func.avg(Review.rating), func.count(Review.id))
            .group_by(Review.warehouse_id).all())
    return jsonify({wid: {"avg": round(float(avg), 2), "count": int(cnt)}
                    for wid, avg, cnt in rows})
