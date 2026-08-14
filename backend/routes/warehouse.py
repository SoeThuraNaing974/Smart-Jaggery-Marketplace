"""Warehouse endpoints: dashboard, batch CRUD, transfers, slips, QR, charts."""
import csv
import io
import os
import uuid
from datetime import datetime, date, timedelta

from datetime import timezone
from dateutil.relativedelta import relativedelta
from flask import Blueprint, request, jsonify, g, Response
from sqlalchemy import func
from werkzeug.utils import secure_filename

from db import db
from models import (
    JaggeryBatch, Order, OrderItem, StockTransfer, Warehouse,
    SubscriptionPlan, WarehouseSubscription, ProductRequest, Payment, BatchImage,
    AbandonedCart,
)
from auth import role_required, audit, verify_password, hash_password
from config import Config
import random
from utils.helpers import packing_slip_pdf, qr_png, payment_slip_pdf, report_pdf, save_image
from utils.email_util import send_bulk, email_enabled
from services import trigger_price_alerts


def _mask_email(email):
    try:
        name, domain = email.split("@", 1)
        shown = name[0] + "***" if name else "***"
        return f"{shown}@{domain}"
    except ValueError:
        return "your email"

bp = Blueprint("warehouse", __name__, url_prefix="/api/warehouse")


def _staff_warehouse_id():
    """Staff are scoped to their own warehouse."""
    return g.current_user.warehouse_id


@bp.get("/stock")
@role_required("warehouse")
def stock():
    wid = _staff_warehouse_id()
    batches = (JaggeryBatch.query.filter_by(warehouse_id=wid)
               .filter(JaggeryBatch.deleted_at.is_(None))
               .order_by(JaggeryBatch.batch_id).all())
    low = [b.to_dict() for b in batches if float(b.qty_kg) < Config.LOW_STOCK_KG]
    # categories the ADMIN removed from this warehouse — newest first, so the
    # warehouse can be notified about deletions on its side
    admin_deleted = (JaggeryBatch.query
                     .filter_by(warehouse_id=wid, deleted_by="admin")
                     .filter(JaggeryBatch.deleted_at.isnot(None))
                     .order_by(JaggeryBatch.deleted_at.desc()).limit(10).all())
    return jsonify({
        "warehouse_id": wid,
        "batches": [b.to_dict() for b in batches],
        "low_stock_alerts": low,
        "low_stock_threshold_kg": Config.LOW_STOCK_KG,
        "admin_deleted": [b.to_dict() for b in admin_deleted],
    })


@bp.get("/abandoned-carts")
@role_required("warehouse")
def abandoned_carts():
    """Carts abandoned in the last 7 days that contain at least one product from
    THIS warehouse — only that warehouse's items are shown to the warehouse."""
    wid = _staff_warehouse_id()
    cutoff = datetime.utcnow() - timedelta(days=7)
    rows = (AbandonedCart.query.filter(AbandonedCart.created_at >= cutoff)
            .order_by(AbandonedCart.created_at.desc()).all())
    # map the referenced batches once, then keep only this warehouse's items
    pks = {int(i.get("batch_pk")) for c in rows for i in (c.items_json or [])
           if str(i.get("batch_pk", "")).lstrip("-").isdigit()}
    batches = {b.id: b for b in JaggeryBatch.query.filter(
        JaggeryBatch.id.in_(pks), JaggeryBatch.warehouse_id == wid).all()} if pks else {}
    out = []
    for c in rows:
        mine = []
        for i in (c.items_json or []):
            b = batches.get(int(i.get("batch_pk", 0) or 0))
            if b:
                mine.append({"batch_id": b.batch_id, "qty_kg": i.get("qty_kg")})
        if mine:
            d = c.to_dict()
            d["items"] = mine
            out.append(d)
    return jsonify(out)


def _own_order_dict(order, wid):
    """Serialize an order as seen by ONE warehouse.

    A cart that mixes products from several warehouses becomes a single order
    assigned to the first item's warehouse, so an assigned order may carry other
    warehouses' items. Staff must only ever see THEIR OWN items and the money
    for those items — never another warehouse's slice. The discount is shared
    in proportion to this warehouse's part of the goods; the delivery charge
    stays with the assigned (delivering) warehouse.
    """
    d = order.to_dict()
    own = [it for it in order.items if it.batch and it.batch.warehouse_id == wid]
    if len(own) == len(order.items):
        return d                                    # entirely this warehouse's order
    own_subtotal = sum(round(float(it.line_total)) for it in own)
    ratio = own_subtotal / float(order.subtotal) if float(order.subtotal or 0) else 0.0
    own_discount = round(float(order.discount_amount) * ratio)
    d["items"] = [it.to_dict() for it in own]
    d["subtotal"] = own_subtotal
    d["discount_amount"] = own_discount
    d["total_price"] = own_subtotal - own_discount
    d["grand_total"] = d["total_price"] + round(float(order.delivery_charge))
    d["partial"] = True          # other warehouses' items exist but are hidden
    return d


@bp.get("/orders")
@role_required("warehouse")
def assigned_orders():
    wid = _staff_warehouse_id()
    # the warehouse never sees unpaid (pending) orders — only paid (waiting) onward
    orders = (
        Order.query.filter(Order.assigned_warehouse_id == wid, Order.status != "pending")
        .order_by(Order.created_at.desc())
        .all()
    )
    return jsonify([_own_order_dict(o, wid) for o in orders])


@bp.get("/orders/unpaid")
@role_required("warehouse")
def unpaid_orders():
    """Customers who still owe this warehouse money — the collection list.

    An order can be unpaid in two ways: pay-on-delivery (already confirmed, so
    it sits in the fulfilment queue as 'waiting'), or an online payment the
    customer never completed ('pending'). /orders above hides 'pending' on
    purpose so nothing unpaid can be shipped — but staff still need to chase
    that money, which is what this list is for, so it includes both.
    """
    wid = _staff_warehouse_id()
    orders = (
        Order.query.filter(Order.assigned_warehouse_id == wid,
                           Order.payment_status != "paid",
                           Order.status != "cancelled")
        .order_by(Order.created_at.desc())
        .all()
    )
    return jsonify([_own_order_dict(o, wid) for o in orders])


@bp.post("/orders/delete")
@role_required("warehouse")
def delete_orders():
    """Bulk-delete orders from this warehouse's history (only its own assigned orders)."""
    wid = _staff_warehouse_id()
    data = request.get_json(silent=True) or {}
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit()]
    if not ids:
        return jsonify({"error": "no orders selected"}), 400
    n = (Order.query
         .filter(Order.id.in_(ids), Order.assigned_warehouse_id == wid)
         .delete(synchronize_session=False))
    db.session.commit()
    return jsonify({"message": "deleted", "count": n})


@bp.get("/orders/history/pdf")
@role_required("warehouse")
def order_history_pdf():
    """Printable PDF of this warehouse's order history (shipped/delivered/cancelled)."""
    wid = _staff_warehouse_id()
    q = Order.query.filter(Order.assigned_warehouse_id == wid,
                           Order.status.in_(["shipped", "cancelled"]))
    dfrom, dto = request.args.get("from"), request.args.get("to")
    if dfrom:
        try:
            q = q.filter(Order.created_at >= datetime.strptime(dfrom, "%Y-%m-%d"))
        except ValueError:
            pass
    if dto:
        try:
            q = q.filter(Order.created_at < datetime.strptime(dto, "%Y-%m-%d") + timedelta(days=1))
        except ValueError:
            pass
    orders = q.order_by(Order.created_at.desc()).all()
    headers = ["No.", "Date", "Customer", "Phone", "Product", "Total (Kyats)", "Status"]
    rows, revenue = [], 0.0
    for n, o in enumerate(orders, start=1):
        # only this warehouse's own items/amounts — never another warehouse's slice
        od = _own_order_dict(o, wid)
        items = ", ".join(it["batch_id"] for it in od["items"] if it.get("batch_id"))
        if len(items) > 38:
            items = items[:35] + "..."
        d = o.created_at.strftime("%Y-%m-%d") if o.created_at else ""
        rows.append([n, d, (o.customer.name if o.customer else ""),
                     (o.customer.phone if o.customer and o.customer.phone else "-"), items,
                     f"{float(od['total_price']):.0f}", o.status])
        if o.status != "cancelled":
            revenue += float(od["total_price"])
    summary = [f"Total orders: {len(rows)}",
               f'<font size="11" color="#7a4a1e"><b>Total amount (excluding cancelled): '
               f'{revenue:,.0f} Kyats</b></font>']
    dates = [r[1] for r in rows if r[1]]
    start = dfrom or (min(dates) if dates else "—")
    end = dto or (max(dates) if dates else "—")
    pdf = report_pdf("Order history", headers, rows, summary, period=f"{start} - {end}")
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=order_history.pdf"})


@bp.post("/batches")
@role_required("warehouse")
def add_batch():
    data = request.get_json(silent=True) or {}
    required = ["batch_id", "grade", "qty_kg", "harvest_date", "price_per_kg"]
    missing = [f for f in required if data.get(f) in (None, "")]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400
    if data["grade"].upper() not in {"A", "B", "C"}:
        return jsonify({"error": "grade must be A, B or C"}), 400
    # category names are NOT unique — the same name may be used freely
    name = data["batch_id"].strip()

    try:
        batch = JaggeryBatch(
            warehouse_id=_staff_warehouse_id(),
            batch_id=name,
            grade=data["grade"].upper(),
            qty_kg=float(data["qty_kg"]),
            harvest_date=datetime.strptime(data["harvest_date"], "%Y-%m-%d").date(),
            price_per_kg=float(data["price_per_kg"]),
        )
        db.session.add(batch)
        db.session.commit()
        return jsonify({"message": "category created", "batch": batch.to_dict()}), 201
    except ValueError:
        return jsonify({"error": "harvest_date must be YYYY-MM-DD, qty/price numeric"}), 400
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@bp.put("/batches/<int:pk>")
@role_required("warehouse")
def update_batch(pk):
    batch = JaggeryBatch.query.filter_by(id=pk, warehouse_id=_staff_warehouse_id()).first()
    if not batch:
        return jsonify({"error": "category not found in your warehouse"}), 404

    data = request.get_json(silent=True) or {}
    try:
        if "batch_id" in data:
            name = (data.get("batch_id") or "").strip()
            if not name:
                return jsonify({"error": "name cannot be empty"}), 400
            # category names are NOT unique — the same name may be used freely
            batch.batch_id = name
        if "qty_kg" in data:
            batch.qty_kg = float(data["qty_kg"])
        fired = 0
        if "price_per_kg" in data:
            old_price = float(batch.price_per_kg)
            batch.price_per_kg = float(data["price_per_kg"])
            if batch.price_per_kg < old_price:  # price dropped -> fire alerts
                fired = trigger_price_alerts(batch)
        if "grade" in data:
            if data["grade"].upper() not in {"A", "B", "C"}:
                return jsonify({"error": "grade must be A, B or C"}), 400
            batch.grade = data["grade"].upper()
        if "harvest_date" in data:
            batch.harvest_date = datetime.strptime(data["harvest_date"], "%Y-%m-%d").date()
        if "description" in data:
            batch.description = (data.get("description") or "").strip() or None
        db.session.commit()
        return jsonify({"message": "category updated", "batch": batch.to_dict(),
                        "price_alerts_fired": fired})
    except ValueError:
        return jsonify({"error": "invalid numeric/date value"}), 400


@bp.delete("/batches/<int:pk>")
@role_required("warehouse")
def warehouse_delete_batch(pk):
    """Warehouse deletes a stock. It's a soft-delete: the product instantly disappears
    from the customer + warehouse views, and the ADMIN is alarmed and shown the deleted
    stock highlighted. Once the admin acknowledges it, it disappears for them too.
    (Soft-delete keeps order history intact and lets the admin review what was removed.)"""
    from datetime import datetime, timezone
    batch = JaggeryBatch.query.filter_by(id=pk, warehouse_id=_staff_warehouse_id()).first()
    if not batch or batch.deleted_at is not None:
        return jsonify({"error": "category not found in your warehouse"}), 404
    name = batch.batch_id
    batch.deleted_at = datetime.now(timezone.utc)
    batch.deleted_by = "warehouse"
    batch.delete_ack = False
    batch.is_active = False
    audit("batch_deleted", f"{name} (WH#{_staff_warehouse_id()})")
    db.session.commit()
    return jsonify({"message": f"{name} deleted — removed from the shop and the admin has been notified"})


@bp.post("/batches/delete")
@role_required("warehouse")
def warehouse_bulk_delete_batches():
    """Bulk soft-delete stock (same as the single delete: hidden from shop, admin alerted)."""
    from datetime import datetime, timezone
    data = request.get_json(silent=True) or {}
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit()]
    if not ids:
        return jsonify({"error": "no products selected"}), 400
    wid = _staff_warehouse_id()
    now = datetime.now(timezone.utc)
    n = 0
    for b in (JaggeryBatch.query
              .filter(JaggeryBatch.id.in_(ids), JaggeryBatch.warehouse_id == wid,
                      JaggeryBatch.deleted_at.is_(None)).all()):
        b.deleted_at = now
        b.deleted_by = "warehouse"
        b.delete_ack = False
        b.is_active = False
        n += 1
    if n:
        audit("batch_deleted_bulk", f"{n} products (WH#{wid})")
        db.session.commit()
    return jsonify({"message": "deleted", "count": n})


@bp.post("/orders/<int:order_id>/status")
@role_required("warehouse")
def update_order_status(order_id):
    """Staff may move: assigned -> packed -> shipped."""
    order = Order.query.filter_by(
        id=order_id, assigned_warehouse_id=_staff_warehouse_id()
    ).first()
    if not order:
        return jsonify({"error": "order not assigned to your warehouse"}), 404

    new_status = (request.get_json(silent=True) or {}).get("status")
    allowed = {"waiting": "shipped"}   # a paid (waiting) order is shipped in one step
    if order.status not in allowed or new_status != allowed[order.status]:
        return jsonify({
            "error": f"cannot move from '{order.status}' to '{new_status}'. "
                     f"Allowed next: {allowed.get(order.status, 'none')}"
        }), 422

    order.status = new_status
    db.session.commit()
    return jsonify({"message": "status updated", "order": order.to_dict()})


@bp.post("/batches/<int:pk>/certificate")
@role_required("warehouse")
def upload_certificate(pk):
    """Multipart upload of a PDF quality certificate, stored locally per batch_id."""
    batch = JaggeryBatch.query.filter_by(id=pk, warehouse_id=_staff_warehouse_id()).first()
    if not batch:
        return jsonify({"error": "category not found in your warehouse"}), 404
    if "file" not in request.files:
        return jsonify({"error": "no file part named 'file'"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "empty filename"}), 400
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in Config.ALLOWED_EXTENSIONS:
        return jsonify({"error": "only PDF certificates are allowed"}), 400

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    safe = secure_filename(f"{batch.batch_id}_{uuid.uuid4().hex[:8]}.pdf")
    path = os.path.join(Config.UPLOAD_FOLDER, safe)
    file.save(path)

    batch.certificate_path = safe  # store relative name
    db.session.commit()
    return jsonify({"message": "certificate uploaded", "certificate_path": safe})


@bp.post("/batches/<int:pk>/images")
@role_required("warehouse")
def warehouse_add_batch_images(pk):
    """Add one or more extra photos to one of this warehouse's own products."""
    batch = JaggeryBatch.query.filter_by(id=pk, warehouse_id=_staff_warehouse_id()).first()
    if not batch:
        return jsonify({"error": "category not found in your warehouse"}), 404
    files = [f for f in (request.files.getlist("files") + request.files.getlist("file")) if f and f.filename]
    if not files:
        return jsonify({"error": "no image files"}), 400
    saved = []
    for f in files:
        try:
            name = save_image(f, prefix=f"batch_{batch.batch_id}")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        if not batch.image_path:
            batch.image_path = name            # cover photo (kept only in image_path)
        else:
            db.session.add(BatchImage(batch_id=batch.id, image_path=name))  # extra photo
        saved.append(name)
    audit("batch_images_add", f"{batch.batch_id} +{len(saved)}")
    db.session.commit()
    return jsonify({"message": f"{len(saved)} image(s) added", "added": saved})


@bp.delete("/batches/<int:pk>/images/<int:img_id>")
@role_required("warehouse")
def warehouse_delete_batch_image(pk, img_id):
    batch = JaggeryBatch.query.filter_by(id=pk, warehouse_id=_staff_warehouse_id()).first()
    if not batch:
        return jsonify({"error": "category not found in your warehouse"}), 404
    img = db.session.get(BatchImage, img_id)
    if not img or img.batch_id != pk:
        return jsonify({"error": "image not found"}), 404
    if batch.image_path == img.image_path:
        batch.image_path = None
    db.session.delete(img)
    db.session.flush()
    if not batch.image_path:
        nxt = BatchImage.query.filter_by(batch_id=pk).first()
        batch.image_path = nxt.image_path if nxt else None
    db.session.commit()
    return jsonify({"message": "image removed"})


@bp.post("/batches/<int:pk>/image")
@role_required("warehouse")
def warehouse_set_cover_image(pk):
    """Set / change the COVER photo for one of this warehouse's own products.
       The cover (batch.image_path) is the single image shown across the whole
       system — customer cards, admin, warehouse — so changing it here updates
       the product picture everywhere at once."""
    batch = JaggeryBatch.query.filter_by(id=pk, warehouse_id=_staff_warehouse_id()).first()
    if not batch:
        return jsonify({"error": "category not found in your warehouse"}), 404
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "no image file"}), 400
    try:
        name = save_image(f, prefix=f"batch_{batch.batch_id}")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    batch.image_path = name
    audit("batch_cover_set", f"{batch.batch_id} -> {name}")
    db.session.commit()
    return jsonify({"message": "cover updated", "image_path": name})


@bp.delete("/batches/<int:pk>/image")
@role_required("warehouse")
def warehouse_remove_cover_image(pk):
    batch = JaggeryBatch.query.filter_by(id=pk, warehouse_id=_staff_warehouse_id()).first()
    if not batch:
        return jsonify({"error": "category not found in your warehouse"}), 404
    batch.image_path = None
    audit("batch_cover_remove", f"{batch.batch_id}")
    db.session.commit()
    return jsonify({"message": "cover removed", "image_path": None})


# ----------------------------------------------------------- dashboard charts
@bp.get("/charts")
@role_required("warehouse")
def dashboard_charts():
    wid = _staff_warehouse_id()
    # stock by grade (pie)
    grade_rows = (db.session.query(JaggeryBatch.grade, func.coalesce(func.sum(JaggeryBatch.qty_kg), 0))
                  .filter(JaggeryBatch.warehouse_id == wid)
                  .group_by(JaggeryBatch.grade).all())
    stock_by_grade = {g_: float(q) for g_, q in grade_rows}

    # last 7 days revenue (line) — only this warehouse's own slice of each order,
    # so the chart agrees with the per-warehouse totals on the Orders page
    today = date.today()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    rev = {d.isoformat(): 0.0 for d in days}
    recent = (Order.query
              .filter(Order.assigned_warehouse_id == wid, Order.status != "cancelled",
                      Order.created_at >= today - timedelta(days=6))
              .all())
    for o in recent:
        key = o.created_at.date().isoformat() if o.created_at else None
        if key in rev:
            rev[key] += float(_own_order_dict(o, wid)["total_price"])
    rev = {k: round(v) for k, v in rev.items()}

    pending = Order.query.filter_by(assigned_warehouse_id=wid, status="waiting").count()
    return jsonify({
        "stock_by_grade": stock_by_grade,
        "revenue_7d": {"labels": list(rev.keys()), "values": list(rev.values())},
        "pending_orders": pending,
    })


# ------------------------------------------------------------ expiry alerts
@bp.get("/expiry-alerts")
@role_required("warehouse")
def expiry_alerts():
    """Batches older than NEAR_EXPIRY_MONTHS (warn) or expired."""
    wid = _staff_warehouse_id()
    batches = JaggeryBatch.query.filter_by(warehouse_id=wid).all()
    flagged = [b.to_dict() for b in batches if b.expiry_status in ("near_expiry", "expired")]
    return jsonify({"alerts": flagged, "count": len(flagged)})


# ------------------------------------------------------ bulk CSV stock upload
@bp.post("/batches/bulk")
@role_required("warehouse")
def bulk_upload():
    """CSV columns: batch_id,grade,qty_kg,harvest_date,price_per_kg"""
    if "file" not in request.files:
        return jsonify({"error": "no file part named 'file'"}), 400
    raw = request.files["file"].read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    wid = _staff_warehouse_id()
    created, errors = 0, []
    for i, row in enumerate(reader, start=2):  # line 1 = header
        try:
            db.session.add(JaggeryBatch(
                warehouse_id=wid, batch_id=row["batch_id"].strip(),
                grade=row["grade"].strip().upper(), qty_kg=float(row["qty_kg"]),
                harvest_date=datetime.strptime(row["harvest_date"].strip(), "%Y-%m-%d").date(),
                price_per_kg=float(row["price_per_kg"]),
            ))
            created += 1
        except (KeyError, ValueError) as e:
            errors.append(f"line {i}: {e}")
    db.session.commit()
    return jsonify({"created": created, "errors": errors})


@bp.get("/sample-stock-template")
@role_required("warehouse")
def sample_stock_template():
    """A printable PDF showing the exact CSV format for the bulk stock upload."""
    headers = ["batch_id", "grade", "qty_kg", "harvest_date", "price_per_kg"]
    rows = [
        ["Cardamom Jaggery", "A", "120", "2026-05-01", "3500"],
        ["Ginger Jaggery", "B", "80", "2026-04-15", "3000"],
        ["Palm Jaggery", "C", "200", "2026-05-20", "2800"],
    ]
    summary = [
        "Save your file as a <b>.csv</b> with these exact 5 columns, in this order:",
        "<b>batch_id</b> — the product name (must be unique).",
        "<b>grade</b> — must be A, B or C.",
        "<b>qty_kg</b> — quantity in kilograms (numbers only).",
        "<b>harvest_date</b> — production date, format YYYY-MM-DD.",
        "<b>price_per_kg</b> — price in Kyats (numbers only).",
    ]
    pdf = report_pdf("Bulk Stock Upload — Sample CSV Format", headers, rows, summary)
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": "inline; filename=sample-stock-format.pdf"})


# ---------------------------------------------------------- stock transfers
@bp.get("/warehouses")
@role_required("warehouse")
def list_all_warehouses():
    """Minimal warehouse list for transfer destination selection."""
    return jsonify([{"id": w.id, "name": w.name, "location": w.location}
                    for w in Warehouse.query.order_by(Warehouse.name).all()])


@bp.get("/transfers")
@role_required("warehouse")
def list_transfers():
    wid = _staff_warehouse_id()
    ts = StockTransfer.query.filter(
        (StockTransfer.from_warehouse_id == wid) | (StockTransfer.to_warehouse_id == wid)
    ).order_by(StockTransfer.requested_at.desc()).all()
    return jsonify([t.to_dict() for t in ts])


@bp.post("/transfers")
@role_required("warehouse")
def request_transfer():
    """Request moving stock to another warehouse (admin approves for v1)."""
    data = request.get_json(silent=True) or {}
    wid = _staff_warehouse_id()
    if not _has_active_subscription(wid):
        return jsonify({"error": "an active subscription is required to request stock transfers"}), 403
    batch = JaggeryBatch.query.filter_by(id=data.get("batch_id"), warehouse_id=wid).first()
    if not batch:
        return jsonify({"error": "category not found in your warehouse"}), 404
    to_wid = data.get("to_warehouse_id")
    if not db.session.get(Warehouse, to_wid) or to_wid == wid:
        return jsonify({"error": "valid destination warehouse required"}), 400
    try:
        qty = float(data["quantity_kg"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "quantity_kg (number) required"}), 400
    if qty <= 0 or qty > float(batch.qty_kg):
        return jsonify({"error": "quantity exceeds available stock"}), 422

    t = StockTransfer(from_warehouse_id=wid, to_warehouse_id=to_wid,
                      batch_id=batch.id, quantity_kg=qty, status="pending")
    db.session.add(t)
    audit("transfer_requested", f"batch {batch.batch_id} {qty}kg -> WH#{to_wid}")
    db.session.commit()
    return jsonify({"message": "transfer requested (awaiting admin approval)", "transfer": t.to_dict()}), 201


# ------------------------------------------------------------- packing slip
@bp.get("/orders/<int:order_id>/packing-slip")
@role_required("warehouse")
def packing_slip(order_id):
    wid = _staff_warehouse_id()
    order = Order.query.filter_by(id=order_id, assigned_warehouse_id=wid).first()
    if not order:
        return jsonify({"error": "order not in your warehouse"}), 404
    pdf = packing_slip_pdf(_own_order_dict(order, wid))
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=packing_{order_id}.pdf"})


# -------------------------------------------------------------- batch QR code
@bp.get("/batches/<int:pk>/qr")
@role_required("warehouse")
def batch_qr(pk):
    batch = JaggeryBatch.query.filter_by(id=pk, warehouse_id=_staff_warehouse_id()).first()
    if not batch:
        return jsonify({"error": "category not found"}), 404
    base = request.host_url.rstrip("/")
    png = qr_png(f"{base}/api/batches?batch={batch.batch_id}|id={batch.id}|grade={batch.grade}")
    return Response(png, mimetype="image/png")


# ----------------------------------------------------- subscription (buy/view)
@bp.get("/subscription-plans")
@role_required("warehouse")
def list_plans():
    plans = SubscriptionPlan.query.filter_by(is_active=True).order_by(
        SubscriptionPlan.duration_months).all()
    return jsonify([p.to_dict() for p in plans])


def _current_subscription(wid):
    """Latest non-cancelled subscription for the warehouse (by end date)."""
    return (WarehouseSubscription.query
            .filter_by(warehouse_id=wid, status="active")
            .order_by(WarehouseSubscription.end_date.desc())
            .first())


@bp.get("/subscription")
@role_required("warehouse")
def my_subscription():
    wid = _staff_warehouse_id()
    sub = _current_subscription(wid)
    history = (WarehouseSubscription.query.filter_by(warehouse_id=wid)
               .order_by(WarehouseSubscription.created_at.desc()).all())
    return jsonify({
        "current": sub.to_dict() if sub else None,
        "active": bool(sub and sub.is_active),
        "history": [h.to_dict() for h in history],
    })


def _pay_otp_valid(user, code):
    if not user.pay_otp_hash or not user.pay_otp_expires:
        return False
    exp = user.pay_otp_expires
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > exp:
        return False
    return verify_password(code or "", user.pay_otp_hash)


@bp.post("/subscription/request-otp")
@role_required("warehouse")
def subscription_request_otp():
    """Email a 6-digit code the warehouse must enter to confirm a subscription payment."""
    user = g.current_user
    code = f"{random.randint(0, 999999):06d}"
    user.pay_otp_hash = hash_password(code)
    user.pay_otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.commit()
    result = send_bulk([user.email], "Your subscription payment code",
                       f"Your code to confirm your subscription payment is {code}. "
                       f"It expires in 10 minutes.")
    audit("subscription_otp_requested", _mask_email(user.email))
    db.session.commit()
    resp = {"sent": True, "email": _mask_email(user.email), "delivery": result.get("status")}
    if not email_enabled():
        resp["dev_code"] = code  # demo: surface the code so it's testable on screen
    return jsonify(resp)


@bp.post("/subscription")
@role_required("warehouse")
def buy_subscription():
    """Buy/extend a plan AFTER payment — confirmed with an emailed OTP. If a
    subscription is still active, the new term stacks on top of the current end date."""
    data = request.get_json(silent=True) or {}
    plan = SubscriptionPlan.query.filter_by(id=data.get("plan_id"), is_active=True).first()
    if not plan:
        return jsonify({"error": "plan not found or inactive"}), 404

    method = (data.get("method") or "").lower()
    if method not in Config.PAYMENT_METHODS:
        return jsonify({"error": f"choose a payment method: {', '.join(sorted(Config.PAYMENT_METHODS))}"}), 400
    reference = (data.get("reference") or "").strip()
    if not reference:
        return jsonify({"error": "transaction reference / slip number is required"}), 400
    if not _pay_otp_valid(g.current_user, (data.get("otp") or "").strip()):
        return jsonify({"error": "invalid or expired verification code"}), 403
    payer = (data.get("payer") or "").strip() or None

    wid = _staff_warehouse_id()
    # Guard against an orphaned account (its warehouse was deleted) — fail with a clear
    # message instead of a database crash when there's no warehouse to attach the subscription to.
    if not wid or not db.session.get(Warehouse, wid):
        return jsonify({"error": "Your account isn't linked to a warehouse (it may have been removed). Please contact the admin to reconnect your account."}), 400
    today = date.today()
    current = _current_subscription(wid)
    base = current.end_date if (current and current.is_active) else today

    sub = WarehouseSubscription(
        warehouse_id=wid, plan_id=plan.id, start_date=today,
        end_date=base + relativedelta(months=plan.duration_months),
        price_paid=plan.price, status="active",
    )
    db.session.add(sub)
    db.session.flush()  # need sub.id for the payment link

    payment = Payment(
        warehouse_id=wid, subscription_id=sub.id, plan_id=plan.id,
        amount=plan.price, method=method, payer=payer, reference=reference, status="paid",
    )
    db.session.add(payment)
    g.current_user.pay_otp_hash = None      # consume the code
    g.current_user.pay_otp_expires = None
    audit("subscription_payment", f"{plan.name} via {method} ref {reference} (WH#{wid})")
    db.session.commit()
    return jsonify({
        "message": f"Payment received — subscribed to {plan.name}",
        "subscription": sub.to_dict(),
        "payment": payment.to_dict(),
    }), 201


@bp.get("/payment-methods")
@role_required("warehouse")
def payment_methods():
    labels = {"kpay": "KPay", "wavepay": "Wave Pay", "ayapay": "AYA Pay",
              "cbpay": "CB Pay", "yomapay": "Yoma Pay", "bank": "Bank Transfer"}
    order = ["kpay", "wavepay", "ayapay", "cbpay", "yomapay", "bank"]
    return jsonify([
        {"key": k, "label": labels[k], "account": Config.MERCHANT_ACCOUNTS.get(k, "")}
        for k in order if k in Config.PAYMENT_METHODS
    ])


@bp.get("/payments")
@role_required("warehouse")
def my_payments():
    rows = (Payment.query.filter_by(warehouse_id=_staff_warehouse_id())
            .order_by(Payment.created_at.desc()).all())
    return jsonify([p.to_dict() for p in rows])


@bp.get("/payments/<int:pid>/slip")
@role_required("warehouse")
def payment_slip(pid):
    """Downloadable PDF receipt for a subscription payment."""
    p = Payment.query.filter_by(id=pid, warehouse_id=_staff_warehouse_id()).first()
    if not p:
        return jsonify({"error": "payment not found"}), 404
    d = p.to_dict()
    pairs = [
        ("Warehouse", d.get("warehouse_name") or ""),
        ("Plan", d.get("plan_name") or ""),
        ("Date", p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else ""),
        ("Payment method", d.get("method_label") or ""),
        ("Reference", d.get("reference") or ""),
        ("Payer", d.get("payer") or ""),
        ("Payment status", (d.get("status") or "").upper()),
    ]
    pdf = payment_slip_pdf("Subscription Payment Receipt", pairs, f"{d['amount']} Kyats",
                           "Thank you for subscribing.")
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=subscription_payment_{p.id}.pdf"})


def _has_active_subscription(wid):
    sub = _current_subscription(wid)
    return bool(sub and sub.is_active)


# ----------------------------------------------- numeric payment PIN (set/verify)
@bp.get("/payment-pin")
@role_required("warehouse")
def payment_pin_status():
    return jsonify({"pin_set": bool(g.current_user.payment_pin_hash)})


@bp.post("/payment-pin")
@role_required("warehouse")
def set_payment_pin():
    """Create/reset the 6-digit payment PIN (KPay-style, set once then entered each pay)."""
    pin = ((request.get_json(silent=True) or {}).get("new_pin") or "").strip()
    if not (pin.isdigit() and len(pin) == 6):
        return jsonify({"error": "PIN must be exactly 6 digits"}), 400
    g.current_user.payment_pin_hash = hash_password(pin)
    audit("payment_pin_set")
    db.session.commit()
    return jsonify({"message": "payment PIN saved"})


@bp.post("/verify-pin")
@role_required("warehouse")
def verify_pin():
    """Verify the numeric payment PIN entered at checkout."""
    if not g.current_user.payment_pin_hash:
        return jsonify({"ok": False, "pin_set": False})
    pin = (request.get_json(silent=True) or {}).get("pin", "")
    return jsonify({"ok": verify_password(pin, g.current_user.payment_pin_hash), "pin_set": True})


# ------------------------------------------- PIN reset via emailed code (OTP)
@bp.post("/pin-reset/request")
@role_required("warehouse")
def pin_reset_request():
    """Email a 6-digit code to the user's assigned email; required to change the PIN."""
    user = g.current_user
    code = f"{random.randint(0, 999999):06d}"
    user.pin_reset_code = hash_password(code)
    # store an aware-UTC instant so the TIMESTAMPTZ column keeps the right time
    user.pin_reset_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.commit()

    result = send_bulk([user.email], "Your PIN reset code",
                       f"Your jaggery payment-PIN reset code is {code}. It expires in 10 minutes.")
    audit("pin_reset_requested", _mask_email(user.email))
    db.session.commit()
    resp = {"sent": True, "email": _mask_email(user.email),
            "delivery": result.get("status")}
    # No live mail server in this demo -> surface the code so it's testable.
    if not email_enabled():
        resp["dev_code"] = code
    return jsonify(resp)


def _reset_code_valid(user, code):
    if not user.pin_reset_code or not user.pin_reset_expires:
        return False
    # column is TIMESTAMPTZ on Postgres (aware) but naive on SQLite — normalize both
    exp = user.pin_reset_expires
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > exp:
        return False
    return verify_password(code or "", user.pin_reset_code)


@bp.post("/pin-reset/verify")
@role_required("warehouse")
def pin_reset_verify():
    code = (request.get_json(silent=True) or {}).get("code", "")
    return jsonify({"ok": _reset_code_valid(g.current_user, code)})


@bp.post("/pin-reset/confirm")
@role_required("warehouse")
def pin_reset_confirm():
    """Set a new PIN — only valid with the emailed code."""
    data = request.get_json(silent=True) or {}
    user = g.current_user
    if not _reset_code_valid(user, data.get("code", "")):
        return jsonify({"error": "invalid or expired verification code"}), 403
    new_pin = (data.get("new_pin") or "").strip()
    if not (new_pin.isdigit() and len(new_pin) == 6):
        return jsonify({"error": "PIN must be exactly 6 digits"}), 400
    user.payment_pin_hash = hash_password(new_pin)
    user.pin_reset_code = None        # consume the code
    user.pin_reset_expires = None
    audit("payment_pin_reset")
    db.session.commit()
    return jsonify({"message": "PIN reset"})


# --------------------------------------- product upload requests (need active sub)
@bp.get("/product-requests")
@role_required("warehouse")
def my_product_requests():
    reqs = (ProductRequest.query.filter_by(warehouse_id=_staff_warehouse_id())
            .order_by(ProductRequest.created_at.desc()).all())
    return jsonify([r.to_dict() for r in reqs])


@bp.post("/product-requests/delete")
@role_required("warehouse")
def delete_product_requests():
    """Bulk-delete this warehouse's own product requests (only its own)."""
    wid = _staff_warehouse_id()
    data = request.get_json(silent=True) or {}
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit()]
    if not ids:
        return jsonify({"error": "no requests selected"}), 400
    n = (ProductRequest.query
         .filter(ProductRequest.id.in_(ids), ProductRequest.warehouse_id == wid)
         .delete(synchronize_session=False))
    db.session.commit()
    return jsonify({"message": "deleted", "count": n})


@bp.post("/product-requests")
@role_required("warehouse")
def submit_product_request():
    """Warehouse asks admin to publish a new product (multipart: fields + optional image).
    Requires an active subscription. Fields: product_name, grade, qty_kg, price_per_kg,
    harvest_date, and optional image file 'file'."""
    wid = _staff_warehouse_id()
    if not _has_active_subscription(wid):
        return jsonify({"error": "an active subscription is required to request product uploads"}), 403

    # accept both multipart form (with image) and plain JSON
    src = request.form if request.form else (request.get_json(silent=True) or {})
    name = (src.get("product_name") or src.get("batch_code") or "").strip()
    grade = (src.get("grade") or "").strip().upper()
    required = {"product_name": name, "grade": grade,
                "qty_kg": src.get("qty_kg"), "price_per_kg": src.get("price_per_kg"),
                "harvest_date": src.get("harvest_date")}
    missing = [k for k, v in required.items() if v in (None, "")]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400
    if grade not in {"A", "B", "C"}:
        return jsonify({"error": "grade must be A, B or C"}), 400
    try:
        qty = float(src["qty_kg"]); price = float(src["price_per_kg"])
        harvest = datetime.strptime(src["harvest_date"], "%Y-%m-%d").date()
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "harvest_date must be YYYY-MM-DD; amount/price numeric"}), 400

    # optional product images (one or many) — first is the cover, rest are extras
    image_path, extras = None, []
    files = [f for f in (request.files.getlist("files") + request.files.getlist("file")) if f and f.filename]
    for i, f in enumerate(files):
        try:
            saved = save_image(f, prefix="req")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        if i == 0:
            image_path = saved
        else:
            extras.append(saved)

    req = ProductRequest(
        warehouse_id=wid, requested_by=g.current_user.id, batch_code=name,
        grade=grade, qty_kg=qty, harvest_date=harvest, price_per_kg=price,
        image_path=image_path,
        extra_images=(",".join(extras) or None),
        description=((src.get("description") or "").strip()[:1000] or None),  # cap at 1000 chars
        status="pending",
    )
    db.session.add(req)
    audit("product_request", f"{name} from WH#{wid}")
    db.session.commit()
    return jsonify({"message": "request submitted for admin approval", "request": req.to_dict()}), 201
