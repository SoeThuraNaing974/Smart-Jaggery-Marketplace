"""Admin endpoints: warehouses, staff, assignment, promotions, analytics, exports."""
import csv
import io
import os
import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify, Response, send_from_directory
from werkzeug.utils import secure_filename
from sqlalchemy import func, or_, text

from db import db
from models import (
    User, Warehouse, Order, OrderItem, Promotion, JaggeryBatch,
    StockTransfer, DeliveryCharge, AbandonedCart, Announcement,
    SubscriptionPlan, WarehouseSubscription, ProductRequest, Payment, BatchImage,
)
from auth import role_required, hash_password, audit
from config import Config
from utils.helpers import report_pdf, to_csv, to_xlsx, pg_dump_backup, backup_slip_pdf, save_image
from utils.email_util import send_bulk, email_enabled
from services import trigger_price_alerts

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ----------------------------------------------------------------- warehouses
@bp.get("/warehouses")
@role_required("admin")
def list_warehouses():
    return jsonify([w.to_dict() for w in Warehouse.query.order_by(Warehouse.name).all()])


@bp.post("/warehouses")
@role_required("admin")
def create_warehouse():
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("location"):
        return jsonify({"error": "name and location are required"}), 400
    w = Warehouse(name=data["name"], location=data["location"],
                  phone=data.get("phone"), email=data.get("email"))
    db.session.add(w)
    db.session.commit()
    return jsonify({"message": "warehouse created", "warehouse": w.to_dict()}), 201


@bp.put("/warehouses/<int:wid>")
@role_required("admin")
def update_warehouse(wid):
    w = db.session.get(Warehouse, wid)
    if not w:
        return jsonify({"error": "warehouse not found"}), 404
    data = request.get_json(silent=True) or {}
    w.name = data.get("name", w.name)
    w.location = data.get("location", w.location)
    w.phone = data.get("phone", w.phone)
    w.email = data.get("email", w.email)
    db.session.commit()
    return jsonify({"message": "updated", "warehouse": w.to_dict()})


def _purge_warehouse(wid):
    """Hard-delete one warehouse and everything tied to it — products, subscriptions/
    payments, stock transfers, product requests — AND its staff login(s), so no
    account is ever left orphaned. Past customer orders are kept (just unassigned).
    Uses direct SQL so the database's ON DELETE rules handle the cascade reliably."""
    from sqlalchemy import text
    # remove the only ON DELETE RESTRICT blocker (line-items for this warehouse's products)
    db.session.execute(text(
        "DELETE FROM order_items WHERE batch_pk IN "
        "(SELECT id FROM jaggery_batches WHERE warehouse_id = :id)"), {"id": wid})
    # remove the warehouse's own staff logins (they exist only to run this warehouse)
    db.session.execute(text(
        "DELETE FROM users WHERE warehouse_id = :id AND role = 'warehouse'"), {"id": wid})
    # delete the warehouse — DB cascades batches/payments/subscriptions/transfers/requests
    db.session.execute(text("DELETE FROM warehouses WHERE id = :id"), {"id": wid})


@bp.delete("/warehouses/<int:wid>")
@role_required("admin")
def delete_warehouse(wid):
    if not db.session.get(Warehouse, wid):
        return jsonify({"error": "warehouse not found"}), 404
    try:
        _purge_warehouse(wid)
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
        return jsonify({"error": "could not delete this warehouse"}), 400
    return jsonify({"message": "warehouse deleted"})


# --- Block / unblock a warehouse (locks out its staff; keeps ALL data) --------
def _parse_block_until():
    """From the request body compute an absolute expiry (aware UTC) or None (no limit).
    Accepts {"until": ISO-8601} (preferred) or {"minutes": <int>}."""
    from datetime import datetime, timezone, timedelta
    data = request.get_json(silent=True) or {}
    until_raw = data.get("until")
    if until_raw:
        try:
            dt = datetime.fromisoformat(str(until_raw).replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None
    try:
        mins = int(data.get("minutes"))
    except (ValueError, TypeError):
        mins = 0
    return datetime.now(timezone.utc) + timedelta(minutes=mins) if mins > 0 else None


def _set_warehouse_blocked(wid, blocked, until=None):
    w = db.session.get(Warehouse, wid)
    if not w:
        return jsonify({"error": "warehouse not found"}), 404
    w.blocked = blocked
    w.blocked_until = until if blocked else None
    audit("warehouse_block" if blocked else "warehouse_unblock",
          f"{w.name}{(' until ' + until.isoformat()) if (blocked and until) else ''}")
    db.session.commit()
    return jsonify({"message": "blocked" if blocked else "unblocked", "id": wid, "blocked": blocked,
                    "blocked_until": w.blocked_until.isoformat() if w.blocked_until else None})


@bp.post("/warehouses/<int:wid>/block")
@role_required("admin")
def block_warehouse(wid):
    return _set_warehouse_blocked(wid, True, _parse_block_until())


@bp.post("/warehouses/<int:wid>/unblock")
@role_required("admin")
def unblock_warehouse(wid):
    return _set_warehouse_blocked(wid, False)


# ---------------------------------------------------------------------- staff
@bp.post("/staff")
@role_required("admin")
def create_staff():
    data = request.get_json(silent=True) or {}
    for f in ("name", "email", "password", "warehouse_id"):
        if not data.get(f):
            return jsonify({"error": f"{f} is required"}), 400
    if not db.session.get(Warehouse, data["warehouse_id"]):
        return jsonify({"error": "warehouse_id does not exist"}), 400
    if User.query.filter_by(email=data["email"].lower()).first():
        return jsonify({"error": "email already registered"}), 409

    staff = User(
        name=data["name"],
        email=data["email"].lower(),
        password_hash=hash_password(data["password"]),
        role="warehouse",
        warehouse_id=data["warehouse_id"],
    )
    db.session.add(staff)
    db.session.commit()
    return jsonify({"message": "staff created", "user": staff.to_dict()}), 201


@bp.get("/staff")
@role_required("admin")
def list_staff():
    staff = User.query.filter_by(role="warehouse").all()
    return jsonify([s.to_dict() for s in staff])


@bp.delete("/staff/<int:uid>")
@role_required("admin")
def delete_staff(uid):
    s = User.query.filter_by(id=uid, role="warehouse").first()
    if not s:
        return jsonify({"error": "staff not found"}), 404
    db.session.delete(s)
    db.session.commit()
    return jsonify({"message": "staff deleted"})


# ------------------------------------------ users & warehouses directory (active?)
@bp.get("/directory")
@role_required("admin")
def admin_directory():
    """All users and warehouses with an Active/Inactive status.
    - user is Active if seen (login / page activity) within the last 30 days
    - warehouse is Active if it has a current (non-expired) active subscription"""
    from datetime import datetime, timezone, timedelta
    from models import WarehouseSubscription
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)

    def _aware(dt):
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    users = User.query.order_by(User.role, User.name).all()
    users_out = []
    for u in users:
        last = _aware(u.last_login)
        users_out.append({
            "id": u.id, "name": u.name, "email": u.email, "role": u.role,
            "warehouse_id": u.warehouse_id,
            "warehouse_name": u.warehouse.name if u.warehouse else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "active": bool(last and last >= cutoff),
            "blocked": u._own_block_active(),
            "blocked_until": u.blocked_until.isoformat() if u.blocked_until else None,
        })

    warehouses = Warehouse.query.order_by(Warehouse.name).all()
    wh_out = []
    for w in warehouses:
        sub = (WarehouseSubscription.query.filter_by(warehouse_id=w.id)
               .order_by(WarehouseSubscription.end_date.desc()).first())
        staff = User.query.filter_by(warehouse_id=w.id, role="warehouse").count()
        wh_out.append({
            "id": w.id, "name": w.name, "location": w.location, "email": w.email,
            "staff_count": staff,
            "active": bool(sub and sub.is_active),
            "subscription": sub.to_dict() if sub else None,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "blocked": w._own_block_active(),
            "blocked_until": w.blocked_until.isoformat() if w.blocked_until else None,
        })

    counts = {
        "users_total": len(users_out),
        "users_active": sum(1 for u in users_out if u["active"]),
        "warehouses_total": len(wh_out),
        "warehouses_active": sum(1 for w in wh_out if w["active"]),
    }
    return jsonify({"users": users_out, "warehouses": wh_out, "counts": counts})


@bp.post("/users/delete")
@role_required("admin")
def delete_users():
    """Bulk-delete users. Admin accounts and the current admin are protected;
    users with un-deletable linked data are skipped (per-item, never errors out)."""
    from flask import g
    data = request.get_json(silent=True) or {}
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit()]
    if not ids:
        return jsonify({"error": "no users selected"}), 400
    deleted, skipped = 0, []
    for uid in ids:
        u = db.session.get(User, uid)
        if not u:
            continue
        if u.role == "admin":
            skipped.append(f"{u.name} (admin)")
            continue
        if u.id == g.current_user.id:
            skipped.append("yourself")
            continue
        try:
            db.session.delete(u)
            db.session.commit()
            deleted += 1
        except Exception:  # noqa: BLE001 — keep going if FKs block one
            db.session.rollback()
            skipped.append(u.name or f"user #{uid}")
    return jsonify({"message": "done", "deleted": deleted, "skipped": skipped})


# --- Block / unblock a single user (locks them out; keeps ALL their data) ------
def _set_user_blocked(uid, blocked, until=None):
    from flask import g
    u = db.session.get(User, uid)
    if not u:
        return jsonify({"error": "user not found"}), 404
    if u.role == "admin":
        return jsonify({"error": "admin accounts cannot be blocked"}), 400
    if u.id == g.current_user.id:
        return jsonify({"error": "you cannot block yourself"}), 400
    u.blocked = blocked
    u.blocked_until = until if blocked else None
    audit("user_block" if blocked else "user_unblock",
          f"{u.name} ({u.email}){(' until ' + until.isoformat()) if (blocked and until) else ''}")
    db.session.commit()
    return jsonify({"message": "blocked" if blocked else "unblocked", "id": uid, "blocked": blocked,
                    "blocked_until": u.blocked_until.isoformat() if u.blocked_until else None})


@bp.post("/users/<int:uid>/block")
@role_required("admin")
def block_user(uid):
    return _set_user_blocked(uid, True, _parse_block_until())


@bp.post("/users/<int:uid>/unblock")
@role_required("admin")
def unblock_user(uid):
    return _set_user_blocked(uid, False)


@bp.post("/warehouses/delete")
@role_required("admin")
def delete_warehouses():
    """Bulk-delete warehouses. Each warehouse and everything tied to it — products,
    subscriptions/payments, transfers, requests, AND its staff login(s) — is removed, so no
    account is ever left orphaned. Past customer orders are kept (just unassigned)."""
    from sqlalchemy import text
    data = request.get_json(silent=True) or {}
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit()]
    if not ids:
        return jsonify({"error": "no warehouses selected"}), 400
    deleted, skipped = 0, []
    for wid in ids:
        row = db.session.execute(text("SELECT name FROM warehouses WHERE id = :id"), {"id": wid}).first()
        if not row:
            continue
        try:
            _purge_warehouse(wid)
            db.session.commit()
            deleted += 1
        except Exception:  # noqa: BLE001
            db.session.rollback()
            skipped.append(row[0] or f"warehouse #{wid}")
    return jsonify({"message": "done", "deleted": deleted, "skipped": skipped})


def _bulk_delete(model, data):
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit()]
    if not ids:
        return None
    n = model.query.filter(model.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return n


@bp.post("/delivery-charges/delete")
@role_required("admin")
def bulk_delete_delivery_charges():
    n = _bulk_delete(DeliveryCharge, request.get_json(silent=True) or {})
    if n is None:
        return jsonify({"error": "no charges selected"}), 400
    return jsonify({"message": "deleted", "count": n})


@bp.post("/announcements/delete")
@role_required("admin")
def bulk_delete_announcements():
    n = _bulk_delete(Announcement, request.get_json(silent=True) or {})
    if n is None:
        return jsonify({"error": "no announcements selected"}), 400
    return jsonify({"message": "deleted", "count": n})


@bp.post("/subscription-plans/delete")
@role_required("admin")
def bulk_delete_subscription_plans():
    n = _bulk_delete(SubscriptionPlan, request.get_json(silent=True) or {})
    if n is None:
        return jsonify({"error": "no plans selected"}), 400
    return jsonify({"message": "deleted", "count": n})


@bp.post("/subscriptions/delete")
@role_required("admin")
def bulk_delete_subscriptions():
    n = _bulk_delete(WarehouseSubscription, request.get_json(silent=True) or {})
    if n is None:
        return jsonify({"error": "no subscriptions selected"}), 400
    return jsonify({"message": "deleted", "count": n})


# ------------------------------------------------------------- order assignment
def _filtered_orders():
    """Orders, newest first, optionally filtered by ?status, ?from, ?to (YYYY-MM-DD)."""
    from datetime import datetime, timezone, timedelta
    q = Order.query
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    dfrom = request.args.get("from")
    dto = request.args.get("to")
    if dfrom:
        try:
            q = q.filter(Order.created_at >= datetime.strptime(dfrom, "%Y-%m-%d").replace(tzinfo=timezone.utc))
        except ValueError:
            pass
    if dto:
        try:
            q = q.filter(Order.created_at < datetime.strptime(dto, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1))
        except ValueError:
            pass
    wh = request.args.get("warehouse")
    if wh:
        q = q.join(Warehouse, Warehouse.id == Order.assigned_warehouse_id).filter(Warehouse.name == wh)
    return q.order_by(Order.created_at.desc()).all()


@bp.get("/orders")
@role_required("admin")
def all_orders():
    return jsonify([o.to_dict() for o in _filtered_orders()])


@bp.get("/orders/pdf")
@role_required("admin")
def orders_pdf_export():
    orders = _filtered_orders()
    headers = ["No.", "Date", "Customer", "Items", "Total (Kyats)", "Warehouse", "Status"]
    rows = []
    total_amount = 0.0
    for n, o in enumerate(orders, start=1):  # sequential list number, matching the on-screen list
        items = ", ".join(f"{it.batch.batch_id} x{float(it.qty_kg):g}kg" for it in o.items if it.batch)
        if len(items) > 42:
            items = items[:39] + "..."
        wh = ", ".join(sorted({it.batch.warehouse.name for it in o.items
                               if it.batch and it.batch.warehouse}))
        d = o.created_at.strftime("%Y-%m-%d") if o.created_at else ""
        rows.append([n, d, (o.customer.name if o.customer else ""), items,
                     f"{o.grand_total:.0f}", wh, o.status])
        if o.status != "cancelled":
            total_amount += float(o.grand_total)
    summary = [f"Total orders: {len(rows)}",
               f'<font size="11" color="#7a4a1e"><b>Total amount (excluding cancelled): '
               f'{total_amount:,.0f} Kyats</b></font>']
    dfrom, dto = request.args.get("from"), request.args.get("to")
    dates = [r[1] for r in rows if r[1]]
    start = dfrom or (min(dates) if dates else "—")
    end = dto or (max(dates) if dates else "—")
    pdf = report_pdf("Orders", headers, rows, summary, period=f"{start} - {end}")
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=orders.pdf"})


@bp.post("/orders/<int:order_id>/assign")
@role_required("admin")
def assign_order(order_id):
    """Admin assigns a pending order to a warehouse (manual for v1)."""
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"error": "order not found"}), 404
    if order.status != "pending":
        return jsonify({"error": "only pending orders can be assigned"}), 422

    wid = (request.get_json(silent=True) or {}).get("warehouse_id")
    warehouse = db.session.get(Warehouse, wid) if wid else None
    if not warehouse:
        return jsonify({"error": "valid warehouse_id required"}), 400

    order.assigned_warehouse_id = warehouse.id   # orders auto-route now; this only re-routes the warehouse
    audit("order_assigned", f"order #{order.id} -> {warehouse.name}")
    db.session.commit()
    return jsonify({"message": "order assigned", "order": order.to_dict()})


@bp.post("/orders/<int:order_id>/deliver")
@role_required("admin")
def mark_delivered(order_id):
    """Deprecated: the order flow now ends at 'shipped' (no separate delivered state)."""
    return jsonify({"error": "the order flow ends at 'shipped' — no delivered step"}), 410


@bp.post("/orders/delete")
@role_required("admin")
def delete_orders():
    """Bulk-delete customer orders (cascades their items, messages & payments)."""
    data = request.get_json(silent=True) or {}
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit()]
    if not ids:
        return jsonify({"error": "no orders selected"}), 400
    n = Order.query.filter(Order.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"message": "deleted", "count": n})


@bp.get("/warehouses/<int:wid>/suggest")
@role_required("admin")
def suggest_capacity(wid):
    """Helper: total available stock at a warehouse to inform assignment."""
    total = db.session.query(func.coalesce(func.sum(JaggeryBatch.qty_kg), 0)).filter(
        JaggeryBatch.warehouse_id == wid
    ).scalar()
    return jsonify({"warehouse_id": wid, "available_kg": float(total)})


# ----------------------------------------------------------------- promotions
@bp.get("/promotions")
@role_required("admin")
def list_promotions():
    return jsonify([p.to_dict() for p in Promotion.query.order_by(Promotion.start_date.desc()).all()])


@bp.post("/promotions")
@role_required("admin")
def create_promotion():
    data = request.get_json(silent=True) or {}
    try:
        promo = Promotion(
            title=data["title"],
            discount_percent=float(data["discount_percent"]),
            min_qty=float(data.get("min_qty", 0)),
            start_date=datetime.strptime(data["start_date"], "%Y-%m-%d").date(),
            end_date=datetime.strptime(data["end_date"], "%Y-%m-%d").date(),
            is_active=bool(data.get("is_active", True)),
        )
    except (KeyError, ValueError):
        return jsonify({"error": "title, discount_percent, start_date, end_date (YYYY-MM-DD) required"}), 400
    if promo.end_date < promo.start_date:
        return jsonify({"error": "end_date must be on/after start_date"}), 400

    db.session.add(promo)
    db.session.commit()
    return jsonify({"message": "promotion created", "promotion": promo.to_dict()}), 201


@bp.put("/promotions/<int:pid>")
@role_required("admin")
def update_promotion(pid):
    promo = db.session.get(Promotion, pid)
    if not promo:
        return jsonify({"error": "promotion not found"}), 404
    data = request.get_json(silent=True) or {}
    try:
        if "title" in data:
            title = (data.get("title") or "").strip()
            if not title:
                return jsonify({"error": "title cannot be empty"}), 400
            promo.title = title
        if "is_active" in data:
            promo.is_active = bool(data["is_active"])
        if "discount_percent" in data:
            dp = float(data["discount_percent"])
            if not (0 <= dp <= 100):
                return jsonify({"error": "discount_percent must be 0-100"}), 400
            promo.discount_percent = dp
        if "min_qty" in data:
            promo.min_qty = float(data["min_qty"])
        if "start_date" in data:
            promo.start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        if "end_date" in data:
            promo.end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return jsonify({"error": "invalid number or date (use YYYY-MM-DD)"}), 400
    if promo.end_date < promo.start_date:
        return jsonify({"error": "end_date must be on/after start_date"}), 400
    audit("promotion_update", promo.title)
    db.session.commit()
    return jsonify({"message": "updated", "promotion": promo.to_dict()})


@bp.delete("/promotions/<int:pid>")
@role_required("admin")
def delete_promotion(pid):
    promo = db.session.get(Promotion, pid)
    if not promo:
        return jsonify({"error": "promotion not found"}), 404
    db.session.delete(promo)
    db.session.commit()
    return jsonify({"message": "promotion deleted"})


# --------------------------------------------------------------------- reports
def _sales_rows(start, end):
    """Aggregate delivered+shipped sales between [start, end)."""
    rows = (
        db.session.query(
            func.date(Order.created_at).label("day"),
            func.coalesce(func.sum(OrderItem.qty_kg), 0).label("qty"),
            func.coalesce(func.sum(Order.total_price), 0).label("revenue"),
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .filter(Order.status != "cancelled")
        .filter(Order.created_at >= start, Order.created_at < end)
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
        .all()
    )
    return rows


@bp.get("/reports")
@role_required("admin")
def reports():
    """?period=daily|weekly|monthly — totals over the trailing window."""
    period = request.args.get("period", "daily")
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 1)
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    rows = _sales_rows(start, end)
    total_qty = sum(float(r.qty) for r in rows)
    total_rev = sum(float(r.revenue) for r in rows)
    return jsonify({
        "period": period,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "total_qty_kg": total_qty,
        "total_revenue": round(total_rev),
        "breakdown": [
            {"date": str(r.day), "qty_kg": float(r.qty), "revenue": round(float(r.revenue))}
            for r in rows
        ],
    })


@bp.get("/reports/export")
@role_required("admin")
def export_csv():
    period = request.args.get("period", "monthly")
    ctx = _report_context(period)

    buf = io.StringIO()
    w = csv.writer(buf)
    # --- report details header ---
    w.writerow(["Smart Jaggery Mart — Sales Report"])
    w.writerow(["Report type", ctx["label"]])
    w.writerow(["Date range", f"{ctx['start']} to {ctx['end']}"])
    w.writerow(["Generated", ctx["generated"]])
    w.writerow(["Total orders", ctx["total_orders"]])
    w.writerow(["Total quantity (kg)", f"{ctx['total_qty']:g}"])
    w.writerow(["Total revenue (Kyats)", f"{ctx['total_rev']:.0f}"])
    w.writerow([])
    # --- daily breakdown ---
    w.writerow(["No.", "Date", "Qty (kg)", "Revenue (Kyats)"])
    for i, d in enumerate(ctx["data"], start=1):
        w.writerow([i, d[0], f"{d[1]:g}", f"{d[2]:.0f}"])
    w.writerow(["", "TOTAL", f"{ctx['total_qty']:g}", f"{ctx['total_rev']:.0f}"])

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sales_{period}.csv"},
    )


# ===================================================================== v2: KPIs
@bp.get("/kpis")
@role_required("admin")
def kpis():
    total_orders = Order.query.filter(Order.status != "cancelled").count()
    total_revenue = round(float(db.session.query(
        func.coalesce(func.sum(Order.total_price + Order.delivery_charge), 0)
    ).filter(Order.status != "cancelled").scalar()))
    active_users = db.session.query(func.count(func.distinct(Order.customer_id))).scalar()
    pending_assignments = Order.query.filter_by(status="pending").count()
    total_stock = float(db.session.query(func.coalesce(func.sum(JaggeryBatch.qty_kg), 0)).scalar())
    total_customers = User.query.filter_by(role="customer").count()
    # admin-focused numbers: platform size, its own subscription income, and work waiting
    total_warehouses = Warehouse.query.count()
    subscription_revenue = round(float(db.session.query(
        func.coalesce(func.sum(Payment.amount), 0)
    ).filter(Payment.status == "paid").scalar()))
    # promotions running right now: switched on and inside their date window
    today = datetime.utcnow().date()
    active_promotions = Promotion.query.filter(
        Promotion.is_active.is_(True),
        Promotion.start_date <= today,
        Promotion.end_date >= today).count()
    # ads live today — same rule as Advertisement.is_live (open-ended dates count)
    from models import Advertisement
    active_ads = Advertisement.query.filter(
        Advertisement.is_active.is_(True),
        or_(Advertisement.starts_on.is_(None), Advertisement.starts_on <= today),
        or_(Advertisement.ends_on.is_(None), Advertisement.ends_on >= today)).count()
    pending_requests = ProductRequest.query.filter_by(status="pending").count()
    return jsonify({
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "active_users": active_users,
        "total_customers": total_customers,
        "pending_assignments": pending_assignments,
        "total_stock_kg": total_stock,
        "total_warehouses": total_warehouses,
        "subscription_revenue": subscription_revenue,
        "active_promotions": active_promotions,
        "active_ads": active_ads,
        "pending_requests": pending_requests,
    })


# ------------------------------------------------------------- dashboard charts
@bp.get("/charts")
@role_required("admin")
def admin_charts():
    # revenue line (last 30 days)
    end = datetime.utcnow().date()
    days = [(end - timedelta(days=i)) for i in range(29, -1, -1)]
    rev = {d.isoformat(): 0.0 for d in days}
    rows = (db.session.query(func.date(Order.created_at), func.coalesce(func.sum(Order.total_price), 0))
            .filter(Order.status != "cancelled", Order.created_at >= end - timedelta(days=29))
            .group_by(func.date(Order.created_at)).all())
    for d, total in rows:
        rev[str(d)] = float(total)

    # top warehouses by orders fulfilled
    top = (db.session.query(Warehouse.name, func.count(Order.id))
           .join(Order, Order.assigned_warehouse_id == Warehouse.id)
           .filter(Order.status != "cancelled")
           .group_by(Warehouse.id).order_by(func.count(Order.id).desc()).limit(5).all())
    return jsonify({
        "revenue_30d": {"labels": list(rev.keys()), "values": [round(v) for v in rev.values()]},
        "top_warehouses": {"labels": [t[0] for t in top], "values": [int(t[1]) for t in top]},
    })


# ------------------------------------------------------- promotion analytics
@bp.get("/promotions/analytics")
@role_required("admin")
def promotion_analytics():
    rows = (db.session.query(
                Promotion.id, Promotion.title,
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_price), 0))
            .outerjoin(Order, Order.promotion_id == Promotion.id)
            .group_by(Promotion.id).order_by(Promotion.id).all())
    return jsonify([
        {"promotion_id": pid, "title": title, "orders": int(cnt), "revenue": round(float(rev))}
        for pid, title, cnt, rev in rows
    ])


# ------------------------------------------------------- export PDF / Excel
_PERIOD_LABEL = {"daily": "Daily (last 1 day)", "weekly": "Weekly (last 7 days)",
                 "monthly": "Monthly (last 30 days)"}


def _report_context(period):
    """Everything an export needs: rows + report details (range, totals, counts)."""
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 30)
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    rows = _sales_rows(start, end)
    data = [[str(r.day), float(r.qty), float(r.revenue)] for r in rows]
    total_qty = sum(d[1] for d in data)
    total_rev = sum(d[2] for d in data)
    total_orders = int((db.session.query(func.count(Order.id))
                        .filter(Order.status != "cancelled",
                                Order.created_at >= start, Order.created_at < end).scalar()) or 0)
    return {
        "period": period,
        "label": _PERIOD_LABEL.get(period, period),
        "start": start.strftime("%Y-%m-%d"),
        "end": end.strftime("%Y-%m-%d"),
        "generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M") + " UTC",
        "days": days,
        "data": data,
        "total_qty": total_qty,
        "total_rev": total_rev,
        "total_orders": total_orders,
    }


@bp.get("/reports/pdf")
@role_required("admin")
def report_pdf_export():
    period = request.args.get("period", "monthly")
    ctx = _report_context(period)
    headers = ["No.", "Date", "Qty (kg)", "Revenue (Kyats)"]
    rows = [[i, d[0], f"{d[1]:g}", f"{d[2]:,.0f}"] for i, d in enumerate(ctx["data"], start=1)]
    rows.append(["", "TOTAL", f"{ctx['total_qty']:g}", f"{ctx['total_rev']:,.0f}"])
    summary = [
        f"Report type: {ctx['label']}",
        f"Total orders: {ctx['total_orders']}  ·  Total quantity: {ctx['total_qty']:g} kg",
        f'<font size="11" color="#7a4a1e"><b>Total revenue: {ctx["total_rev"]:,.0f} Kyats</b></font>',
    ]
    pdf = report_pdf("Sales Report", headers, rows, summary, period=f"{ctx['start']} - {ctx['end']}")
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=sales_{period}.pdf"})


@bp.get("/reports/excel")
@role_required("admin")
def report_excel_export():
    period = request.args.get("period", "monthly")
    ctx = _report_context(period)
    headers = ["No.", "Date", "Qty (kg)", "Revenue (Kyats)"]
    rows = [[i, d[0], round(d[1], 2), round(d[2])] for i, d in enumerate(ctx["data"], start=1)]
    info_lines = [
        ["Smart Jaggery Mart — Sales Report"],
        ["Report type", ctx["label"]],
        ["Date range", f"{ctx['start']} to {ctx['end']}"],
        ["Generated", ctx["generated"]],
        ["Total orders", ctx["total_orders"]],
        ["Total quantity (kg)", round(ctx["total_qty"], 2)],
        ["Total revenue (Kyats)", round(ctx["total_rev"])],
    ]
    total_row = ["", "TOTAL", round(ctx["total_qty"], 2), round(ctx["total_rev"])]
    xlsx = to_xlsx(headers, rows, f"Sales {period}", info_lines=info_lines, total_row=total_row)
    return Response(
        xlsx,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=sales_{period}.xlsx"},
    )


# ----------------------------------------------------- one-click DB backup
@bp.post("/backup")
@role_required("admin")
def backup():
    from flask import g
    filename, err = pg_dump_backup()
    if err:
        return jsonify({"error": err}), 500
    audit("db_backup", filename)
    db.session.commit()

    # build an attractive PDF report of the database details (every table + record count)
    path = os.path.join(Config.UPLOAD_FOLDER, filename)
    size_kb = round(os.path.getsize(path) / 1024.0, 1) if os.path.exists(path) else 0
    dbname = Config.SQLALCHEMY_DATABASE_URI.rsplit("/", 1)[-1]
    admin_name = getattr(getattr(g, "current_user", None), "name", None) or "Admin"

    table_names = [r[0] for r in db.session.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' ORDER BY table_name"
    )).fetchall()]
    rows, total = [], 0
    for i, t in enumerate(table_names, start=1):
        try:
            cnt = db.session.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
        except Exception:  # noqa: BLE001
            cnt = 0
        rows.append([i, t, f"{cnt:,}"])
        total += cnt

    summary = [
        f"Backup file: {filename}",
        f"Database: {dbname}  ·  File size: {size_kb:,} KB",
        f"Created by: {admin_name}  ·  Saved to: backend/uploads/",
        f"Total tables: {len(rows)}  ·  Total records: {total:,}",
        '<font size="11" color="#7a4a1e"><b>Status: BACKUP SUCCESSFUL</b></font>',
    ]
    pdf = report_pdf("Database Backup — Details", ["No.", "Table", "Records"], rows, summary)
    out_name = "database_details_" + filename.replace("backup_", "").replace(".sql", "") + ".pdf"
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={out_name}"})


# ------------------------------------------------- bulk email recipient list
@bp.get("/customers/emails")
@role_required("admin")
def customer_emails():
    custs = User.query.filter_by(role="customer").all()
    return jsonify({"count": len(custs), "emails": [c.email for c in custs],
                    "email_enabled": email_enabled()})


@bp.post("/email/bulk")
@role_required("admin")
def send_bulk_email():
    """Send a promotional email to all customers (real SMTP, or dry-run if unset)."""
    data = request.get_json(silent=True) or {}
    subject = (data.get("subject") or "").strip()
    body = (data.get("body") or "").strip()
    if not subject or not body:
        return jsonify({"error": "subject and body are required"}), 400

    recipients = [c.email for c in User.query.filter_by(role="customer").all()]
    try:
        result = send_bulk(recipients, subject, body)
    except Exception as exc:  # noqa: BLE001 — surface SMTP errors cleanly
        return jsonify({"error": f"email send failed: {exc}"}), 502

    audit("bulk_email", f"{result.get('status')} to {result.get('count')} recipients: {subject}")
    db.session.commit()
    return jsonify(result)


# -------------------------------------------------------- delivery charges
@bp.get("/delivery-charges")
@role_required("admin")
def list_delivery_charges():
    return jsonify([d.to_dict() for d in DeliveryCharge.query.order_by(DeliveryCharge.pincode).all()])


@bp.post("/delivery-charges")
@role_required("admin")
def upsert_delivery_charge():
    data = request.get_json(silent=True) or {}
    pincode = (data.get("pincode") or "").strip()
    if not pincode:
        return jsonify({"error": "pincode required"}), 400
    try:
        amount = float(data["charge_amount"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "charge_amount (number) required"}), 400
    # Foreign locations (a shipping country or the "Foreign" catch-all) are kept
    # inside the 20k–50k Kyats band, so the table always shows what is charged.
    key = pincode.lower()
    if key in Config.FOREIGN_COUNTRY_FEES or key == "foreign":
        amount = min(max(amount, Config.FOREIGN_FEE_MIN), Config.FOREIGN_FEE_MAX)
    dc = DeliveryCharge.query.filter_by(pincode=pincode).first()
    if dc:
        dc.charge_amount = amount
    else:
        dc = DeliveryCharge(pincode=pincode, charge_amount=amount)
        db.session.add(dc)
    db.session.commit()
    return jsonify({"message": "saved", "delivery_charge": dc.to_dict()})


@bp.delete("/delivery-charges/<int:cid>")
@role_required("admin")
def delete_delivery_charge(cid):
    dc = db.session.get(DeliveryCharge, cid)
    if dc:
        db.session.delete(dc)
        db.session.commit()
    return jsonify({"message": "deleted"})


# ----------------------------------------------------------- abandoned carts
@bp.get("/abandoned-carts")
@role_required("admin")
def abandoned_carts():
    cutoff = datetime.utcnow() - timedelta(days=7)
    rows = AbandonedCart.query.filter(AbandonedCart.created_at >= cutoff).order_by(
        AbandonedCart.created_at.desc()).all()
    return jsonify([a.to_dict() for a in rows])


@bp.post("/abandoned-carts/delete")
@role_required("admin")
def delete_abandoned_carts():
    data = request.get_json(silent=True) or {}
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit()]
    if not ids:
        return jsonify({"error": "no carts selected"}), 400
    n = AbandonedCart.query.filter(AbandonedCart.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"message": "deleted", "count": n})


# ------------------------------------------------------------- site content
@bp.put("/content/<key>")
@role_required("admin")
def save_site_content(key):
    """Upsert the admin-edited copy for a public page (About Us). Blank fields
    are dropped so the template's built-in bilingual defaults show again."""
    from models import SiteContent
    if key not in ("about",):
        return jsonify({"error": "unknown content key"}), 404
    data = request.get_json(silent=True) or {}
    fields = {}
    for k, v in data.items():
        if isinstance(v, (str, int, float)) and str(v).strip():
            fields[str(k)[:40]] = str(v).strip()[:2000]
    row = db.session.get(SiteContent, key)
    if not row:
        row = SiteContent(key=key)
        db.session.add(row)
    row.data = fields
    db.session.commit()
    audit("site_content_saved", f"key={key} fields={sorted(fields.keys())}")
    return jsonify({"message": "saved", "content": row.to_dict()})


# ------------------------------------------------------------- announcements
@bp.get("/announcements")
@role_required("admin")
def list_announcements_admin():
    return jsonify([a.to_dict() for a in Announcement.query.order_by(Announcement.created_at.desc()).all()])


@bp.post("/announcements")
@role_required("admin")
def create_announcement():
    from flask import g
    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("message"):
        return jsonify({"error": "title and message required"}), 400
    exp = None
    if data.get("expires_at"):
        try:
            exp = datetime.strptime(data["expires_at"], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "expires_at must be YYYY-MM-DD"}), 400
    a = Announcement(title=data["title"], message=data["message"],
                     created_by_admin_id=g.current_user.id, expires_at=exp)
    db.session.add(a)
    db.session.commit()
    return jsonify({"message": "announcement posted", "announcement": a.to_dict()}), 201


@bp.delete("/announcements/<int:aid>")
@role_required("admin")
def delete_announcement(aid):
    a = db.session.get(Announcement, aid)
    if a:
        db.session.delete(a)
        db.session.commit()
    return jsonify({"message": "deleted"})


# ------------------------------------------------------------- advertisements
_AD_ACCENTS = {"amber", "green", "red", "blue", "purple", "teal", "pink"}


def _parse_date(value, field):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{field} must be YYYY-MM-DD")


def _norm_url(value):
    """Normalise a CTA link so the button always reaches a real destination.
    - blank            -> None
    - '/path'          -> kept (internal page on this site)
    - 'http(s)://...'  -> kept (external site)
    - 'example.com'    -> 'https://example.com' (so it isn't treated as a local path)
    """
    u = (value or "").strip()
    if not u:
        return None
    if u.startswith("/") or u.startswith("http://") or u.startswith("https://"):
        return u
    return "https://" + u


@bp.get("/advertisements")
@role_required("admin")
def list_advertisements_admin():
    from models import Advertisement
    rows = Advertisement.query.order_by(Advertisement.created_at.desc()).all()
    return jsonify([a.to_dict() for a in rows])


@bp.post("/advertisements")
@role_required("admin")
def create_advertisement():
    from flask import g
    from models import Advertisement
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    accent = (data.get("accent") or "amber").strip().lower()
    if accent not in _AD_ACCENTS:
        accent = "amber"
    icon = (data.get("icon") or "📣").strip()[:16] or "📣"
    try:
        starts_on = _parse_date(data.get("starts_on"), "starts_on")
        ends_on = _parse_date(data.get("ends_on"), "ends_on")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if starts_on and ends_on and ends_on < starts_on:
        return jsonify({"error": "end date cannot be before start date"}), 400
    ad = Advertisement(
        title=title,
        body=(data.get("body") or "").strip() or None,
        icon=icon,
        accent=accent,
        link_url=_norm_url(data.get("link_url")),
        link_label=(data.get("link_label") or "").strip() or None,
        is_active=bool(data.get("is_active", True)),
        starts_on=starts_on,
        ends_on=ends_on,
        created_by_admin_id=g.current_user.id,
    )
    db.session.add(ad)
    db.session.commit()
    return jsonify({"message": "advertisement created", "advertisement": ad.to_dict()}), 201


@bp.put("/advertisements/<int:aid>")
@role_required("admin")
def update_advertisement(aid):
    from models import Advertisement
    ad = db.session.get(Advertisement, aid)
    if not ad:
        return jsonify({"error": "advertisement not found"}), 404
    data = request.get_json(silent=True) or {}
    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400
        ad.title = title
    if "body" in data:
        ad.body = (data.get("body") or "").strip() or None
    if "icon" in data:
        ad.icon = (data.get("icon") or "📣").strip()[:16] or "📣"
    if "accent" in data:
        accent = (data.get("accent") or "amber").strip().lower()
        ad.accent = accent if accent in _AD_ACCENTS else "amber"
    if "link_url" in data:
        ad.link_url = _norm_url(data.get("link_url"))
    if "link_label" in data:
        ad.link_label = (data.get("link_label") or "").strip() or None
    if "is_active" in data:
        ad.is_active = bool(data.get("is_active"))
    try:
        if "starts_on" in data:
            ad.starts_on = _parse_date(data.get("starts_on"), "starts_on")
        if "ends_on" in data:
            ad.ends_on = _parse_date(data.get("ends_on"), "ends_on")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if ad.starts_on and ad.ends_on and ad.ends_on < ad.starts_on:
        return jsonify({"error": "end date cannot be before start date"}), 400
    db.session.commit()
    return jsonify({"message": "advertisement updated", "advertisement": ad.to_dict()})


@bp.delete("/advertisements/<int:aid>")
@role_required("admin")
def delete_advertisement(aid):
    from models import Advertisement
    ad = db.session.get(Advertisement, aid)
    if ad:
        db.session.delete(ad)
        db.session.commit()
    return jsonify({"message": "deleted"})


# --------------------------------------------------- stock transfer approval
@bp.get("/transfers")
@role_required("admin")
def all_transfers():
    status = request.args.get("status")
    q = StockTransfer.query
    if status:
        q = q.filter_by(status=status)
    return jsonify([t.to_dict() for t in q.order_by(StockTransfer.requested_at.desc()).all()])


@bp.post("/transfers/delete")
@role_required("admin")
def delete_transfers():
    data = request.get_json(silent=True) or {}
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit()]
    if not ids:
        return jsonify({"error": "no transfers selected"}), 400
    n = StockTransfer.query.filter(StockTransfer.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"message": "deleted", "count": n})


@bp.post("/transfers/<int:tid>/decision")
@role_required("admin")
def decide_transfer(tid):
    from flask import g
    t = db.session.get(StockTransfer, tid)
    if not t:
        return jsonify({"error": "transfer not found"}), 404
    if t.status != "pending":
        return jsonify({"error": "transfer already decided"}), 422
    decision = (request.get_json(silent=True) or {}).get("decision")
    if decision not in ("approved", "rejected"):
        return jsonify({"error": "decision must be 'approved' or 'rejected'"}), 400

    if decision == "approved":
        src = db.session.get(JaggeryBatch, t.batch_id)
        if not src or float(src.qty_kg) < float(t.quantity_kg):
            return jsonify({"error": "source category lacks stock"}), 422
        # move stock: decrement source, create/increment a batch at destination
        src.qty_kg = float(src.qty_kg) - float(t.quantity_kg)
        dest_code = f"{src.batch_id}-T{t.id}"
        dest = JaggeryBatch(warehouse_id=t.to_warehouse_id, batch_id=dest_code,
                            grade=src.grade, qty_kg=float(t.quantity_kg),
                            harvest_date=src.harvest_date, price_per_kg=src.price_per_kg)
        db.session.add(dest)
        t.status = "completed"
    else:
        t.status = "rejected"
    t.approved_by_admin_id = g.current_user.id
    audit("transfer_decision", f"transfer #{t.id} -> {t.status}")
    db.session.commit()
    return jsonify({"message": f"transfer {t.status}", "transfer": t.to_dict()})


# ============================================= warehouse product upload requests
@bp.get("/product-requests")
@role_required("admin")
def list_product_requests():
    status = request.args.get("status")
    q = ProductRequest.query
    if status:
        q = q.filter_by(status=status)
    reqs = q.order_by(ProductRequest.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reqs])


@bp.post("/product-requests/<int:rid>/decision")
@role_required("admin")
def decide_product_request(rid):
    """Approve -> publish a real batch in that warehouse. Reject -> mark rejected."""
    from flask import g
    req = db.session.get(ProductRequest, rid)
    if not req:
        return jsonify({"error": "request not found"}), 404
    if req.status != "pending":
        return jsonify({"error": "request already decided"}), 422

    data = request.get_json(silent=True) or {}
    decision = data.get("decision")
    if decision not in ("approved", "rejected"):
        return jsonify({"error": "decision must be 'approved' or 'rejected'"}), 400

    req.admin_note = (data.get("note") or "").strip() or None
    req.reviewed_by = g.current_user.id
    req.reviewed_at = datetime.utcnow()

    if decision == "rejected":
        req.status = "rejected"
        audit("product_request_rejected", req.batch_code)
        db.session.commit()
        return jsonify({"message": "request rejected", "request": req.to_dict()})

    # approved -> create the live batch (the warehouse can now see it in batches);
    # category names are NOT unique, so an existing name never blocks approval
    batch = JaggeryBatch(
        warehouse_id=req.warehouse_id, batch_id=req.batch_code, grade=req.grade,
        qty_kg=req.qty_kg, harvest_date=req.harvest_date, price_per_kg=req.price_per_kg,
        image_path=req.image_path, description=req.description, is_active=True,
    )
    db.session.add(batch)
    db.session.flush()
    # carry over any extra photos the warehouse attached to the request
    for name in (req.extra_images or "").split(","):
        name = name.strip()
        if name:
            db.session.add(BatchImage(batch_id=batch.id, image_path=name))
    req.status = "approved"
    req.created_batch_id = batch.id
    audit("product_request_approved", f"{req.batch_code} -> batch #{batch.id}")
    db.session.commit()
    return jsonify({"message": "approved and published to categories",
                    "request": req.to_dict(), "batch": batch.to_dict()})


# ==================================================== subscription plan management
@bp.get("/subscription-plans")
@role_required("admin")
def list_plans_admin():
    plans = SubscriptionPlan.query.order_by(SubscriptionPlan.duration_months).all()
    return jsonify([p.to_dict() for p in plans])


@bp.post("/subscription-plans")
@role_required("admin")
def create_plan():
    data = request.get_json(silent=True) or {}
    try:
        name = (data["name"] or "").strip()
        months = int(data["duration_months"])
        price = float(data["price"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "name, duration_months (int), price (number) required"}), 400
    if not name or months <= 0 or price < 0:
        return jsonify({"error": "invalid name/duration/price"}), 400
    plan = SubscriptionPlan(name=name, duration_months=months, price=price,
                            is_active=bool(data.get("is_active", True)))
    db.session.add(plan)
    audit("plan_create", name)
    db.session.commit()
    return jsonify({"message": "plan created", "plan": plan.to_dict()}), 201


@bp.put("/subscription-plans/<int:pid>")
@role_required("admin")
def update_plan(pid):
    plan = db.session.get(SubscriptionPlan, pid)
    if not plan:
        return jsonify({"error": "plan not found"}), 404
    data = request.get_json(silent=True) or {}
    try:
        if "name" in data:
            if not (data["name"] or "").strip():
                return jsonify({"error": "name cannot be empty"}), 400
            plan.name = data["name"].strip()
        if "duration_months" in data:
            m = int(data["duration_months"])
            if m <= 0:
                return jsonify({"error": "duration_months must be > 0"}), 400
            plan.duration_months = m
        if "price" in data:
            plan.price = float(data["price"])
        if "is_active" in data:
            plan.is_active = bool(data["is_active"])
    except (ValueError, TypeError):
        return jsonify({"error": "invalid number"}), 400
    audit("plan_update", plan.name)
    db.session.commit()
    return jsonify({"message": "plan updated", "plan": plan.to_dict()})


@bp.delete("/subscription-plans/<int:pid>")
@role_required("admin")
def delete_plan(pid):
    plan = db.session.get(SubscriptionPlan, pid)
    if not plan:
        return jsonify({"error": "plan not found"}), 404
    if WarehouseSubscription.query.filter_by(plan_id=pid).first():
        return jsonify({"error": "plan has subscriptions; set is_active=false instead"}), 409
    name = plan.name
    db.session.delete(plan)
    audit("plan_delete", name)
    db.session.commit()
    return jsonify({"message": "plan deleted"})


@bp.delete("/subscriptions/<int:sid>")
@role_required("admin")
def delete_subscription(sid):
    sub = db.session.get(WarehouseSubscription, sid)
    if not sub:
        return jsonify({"error": "subscription not found"}), 404
    wh = sub.warehouse.name if sub.warehouse else str(sub.warehouse_id)
    db.session.delete(sub)
    audit("subscription_delete", wh)
    db.session.commit()
    return jsonify({"message": "subscription deleted"})


@bp.get("/payments")
@role_required("admin")
def all_payments():
    q = Payment.query
    # optional date range filter on created_at (naive UTC timestamp)
    from datetime import datetime, timedelta
    dfrom, dto = request.args.get("from"), request.args.get("to")
    if dfrom:
        try:
            q = q.filter(Payment.created_at >= datetime.strptime(dfrom, "%Y-%m-%d"))
        except ValueError:
            pass
    if dto:
        try:
            q = q.filter(Payment.created_at < datetime.strptime(dto, "%Y-%m-%d") + timedelta(days=1))
        except ValueError:
            pass
    wh = request.args.get("warehouse")
    if wh:
        q = q.join(Warehouse, Warehouse.id == Payment.warehouse_id).filter(Warehouse.name == wh)
    rows = q.order_by(Payment.created_at.desc()).limit(500).all()
    # total_collected is always the overall paid total (not affected by the filter)
    total = round(float(db.session.query(func.coalesce(func.sum(Payment.amount), 0))
                  .filter(Payment.status == "paid").scalar()))
    return jsonify({"total_collected": total, "payments": [p.to_dict() for p in rows]})


@bp.post("/payments/delete")
@role_required("admin")
def delete_payments():
    """Bulk-delete payment records (the receipts only — subscriptions stay active)."""
    data = request.get_json(silent=True) or {}
    ids = [int(x) for x in (data.get("ids") or []) if str(x).isdigit()]
    if not ids:
        return jsonify({"error": "no payments selected"}), 400
    deleted = 0
    for pid in ids:
        p = db.session.get(Payment, pid)
        if not p:
            continue
        try:
            db.session.delete(p)
            db.session.commit()
            deleted += 1
        except Exception:  # noqa: BLE001
            db.session.rollback()
    return jsonify({"message": "done", "deleted": deleted})


@bp.get("/payments/pdf")
@role_required("admin")
def payments_pdf_export():
    """Branded PDF slip of subscription payments received (filter by warehouse + date)."""
    from datetime import datetime, timedelta
    q = Payment.query
    dfrom, dto = request.args.get("from"), request.args.get("to")
    if dfrom:
        try:
            q = q.filter(Payment.created_at >= datetime.strptime(dfrom, "%Y-%m-%d"))
        except ValueError:
            pass
    if dto:
        try:
            q = q.filter(Payment.created_at < datetime.strptime(dto, "%Y-%m-%d") + timedelta(days=1))
        except ValueError:
            pass
    wh = request.args.get("warehouse")
    if wh:
        q = q.join(Warehouse, Warehouse.id == Payment.warehouse_id).filter(Warehouse.name == wh)
    payments = q.order_by(Payment.created_at.desc()).limit(500).all()

    labels = {"kpay": "KPay", "wavepay": "Wave Pay", "ayapay": "AYA Pay",
              "cbpay": "CB Pay", "yomapay": "Yoma Pay", "bank": "Bank Transfer"}
    headers = ["No.", "Date", "Warehouse", "Plan", "Amount (Kyats)", "Method", "Reference", "Status"]
    rows = []
    total_received = 0.0
    for n, p in enumerate(payments, start=1):
        d = p.created_at.strftime("%Y-%m-%d") if p.created_at else ""
        rows.append([n, d,
                     (p.warehouse.name if p.warehouse else ""),
                     (p.plan.name if p.plan else "—"),
                     f"{float(p.amount):.0f}",
                     labels.get(p.method, p.method),
                     (p.reference or "—"),
                     p.status])
        if p.status == "paid":
            total_received += float(p.amount)
    summary = [f"Total payments: {len(rows)}",
               f'<font size="11" color="#7a4a1e"><b>Total received: '
               f'{total_received:,.0f} Kyats</b></font>']
    dates = [r[1] for r in rows if r[1]]
    start = dfrom or (min(dates) if dates else "—")
    end = dto or (max(dates) if dates else "—")
    title = "Subscription Payments Received"
    if wh:
        title += f" - {wh}"
    pdf = report_pdf(title, headers, rows, summary, period=f"{start} - {end}")
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=payments.pdf"})


@bp.get("/subscriptions")
@role_required("admin")
def all_subscriptions():
    """Every warehouse's current subscription status (for the admin overview)."""
    out = []
    for w in Warehouse.query.order_by(Warehouse.name).all():
        sub = (WarehouseSubscription.query
               .filter_by(warehouse_id=w.id, status="active")
               .order_by(WarehouseSubscription.end_date.desc()).first())
        out.append({
            "warehouse_id": w.id, "warehouse": w.name,
            "subscribed": bool(sub and sub.is_active),
            "current": sub.to_dict() if sub else None,
        })
    return jsonify(out)


# =============================================== admin batch CRUD (all warehouses)
# --------------------------------------------------- stock deleted by warehouses
@bp.get("/deleted-stocks")
@role_required("admin")
def admin_deleted_stocks():
    """Stocks a warehouse deleted that the admin hasn't acknowledged yet."""
    rows = (JaggeryBatch.query
            .filter(JaggeryBatch.deleted_at.isnot(None), JaggeryBatch.delete_ack.is_(False))
            .order_by(JaggeryBatch.deleted_at.desc()).all())
    return jsonify([b.to_dict() for b in rows])


@bp.post("/deleted-stocks/<int:pk>/ack")
@role_required("admin")
def admin_ack_deleted_stock(pk):
    """Admin checked the deletion → it disappears from the admin view."""
    b = JaggeryBatch.query.filter(JaggeryBatch.id == pk, JaggeryBatch.deleted_at.isnot(None)).first()
    if not b:
        return jsonify({"error": "deleted stock not found"}), 404
    b.delete_ack = True
    audit("deleted_stock_ack", b.batch_id)
    db.session.commit()
    return jsonify({"message": "acknowledged"})


@bp.post("/deleted-stocks/ack-all")
@role_required("admin")
def admin_ack_all_deleted_stocks():
    n = (JaggeryBatch.query
         .filter(JaggeryBatch.deleted_at.isnot(None), JaggeryBatch.delete_ack.is_(False))
         .update({JaggeryBatch.delete_ack: True}, synchronize_session=False))
    db.session.commit()
    return jsonify({"message": "all acknowledged", "count": n})


@bp.get("/batches")
@role_required("admin")
def admin_list_batches():
    """List batches across every warehouse. Filters: ?warehouse_id=&grade=&active="""
    q = JaggeryBatch.query.filter(JaggeryBatch.deleted_at.is_(None))   # deleted stock shown separately
    if request.args.get("warehouse_id", type=int):
        q = q.filter_by(warehouse_id=request.args.get("warehouse_id", type=int))
    if request.args.get("grade"):
        q = q.filter_by(grade=request.args["grade"].upper())
    active = request.args.get("active")
    if active in ("true", "false"):
        q = q.filter_by(is_active=(active == "true"))
    # optional added-date range filter (created_at is a naive UTC timestamp)
    from datetime import datetime, timedelta
    dfrom, dto = request.args.get("from"), request.args.get("to")
    if dfrom:
        try:
            q = q.filter(JaggeryBatch.created_at >= datetime.strptime(dfrom, "%Y-%m-%d"))
        except ValueError:
            pass
    if dto:
        try:
            q = q.filter(JaggeryBatch.created_at < datetime.strptime(dto, "%Y-%m-%d") + timedelta(days=1))
        except ValueError:
            pass
    batches = q.order_by(JaggeryBatch.created_at.desc()).all()
    return jsonify([b.to_dict() for b in batches])


@bp.post("/batches")
@role_required("admin")
def admin_create_batch():
    data = request.get_json(silent=True) or {}
    required = ["warehouse_id", "batch_id", "grade", "qty_kg", "harvest_date", "price_per_kg"]
    missing = [f for f in required if data.get(f) in (None, "")]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400
    if not db.session.get(Warehouse, data["warehouse_id"]):
        return jsonify({"error": "warehouse_id does not exist"}), 400
    if data["grade"].upper() not in {"A", "B", "C"}:
        return jsonify({"error": "grade must be A, B or C"}), 400
    # category names are NOT unique — the same name may be used freely
    try:
        batch = JaggeryBatch(
            warehouse_id=int(data["warehouse_id"]),
            batch_id=data["batch_id"].strip(),
            grade=data["grade"].upper(),
            qty_kg=float(data["qty_kg"]),
            harvest_date=datetime.strptime(data["harvest_date"], "%Y-%m-%d").date(),
            price_per_kg=float(data["price_per_kg"]),
            description=((data.get("description") or "").strip()[:1000] or None),
            is_active=bool(data.get("is_active", True)),
        )
        db.session.add(batch)
        audit("batch_create", f"{batch.batch_id} @ WH#{batch.warehouse_id}")
        db.session.commit()
        return jsonify({"message": "category created", "batch": batch.to_dict()}), 201
    except ValueError:
        return jsonify({"error": "harvest_date must be YYYY-MM-DD; qty/price numeric"}), 400


@bp.put("/batches/<int:pk>")
@role_required("admin")
def admin_update_batch(pk):
    batch = db.session.get(JaggeryBatch, pk)
    if not batch:
        return jsonify({"error": "category not found"}), 404
    data = request.get_json(silent=True) or {}
    fired = 0
    try:
        if "warehouse_id" in data:
            if not db.session.get(Warehouse, data["warehouse_id"]):
                return jsonify({"error": "warehouse_id does not exist"}), 400
            batch.warehouse_id = int(data["warehouse_id"])
        if "batch_id" in data:
            name = data["batch_id"].strip()
            if not name:
                return jsonify({"error": "name cannot be empty"}), 400
            # category names are NOT unique — the same name may be used freely
            batch.batch_id = name
        if "qty_kg" in data:
            batch.qty_kg = float(data["qty_kg"])
        if "price_per_kg" in data:
            old = float(batch.price_per_kg)
            batch.price_per_kg = float(data["price_per_kg"])
            if batch.price_per_kg < old:
                fired = trigger_price_alerts(batch)
        if "grade" in data:
            if data["grade"].upper() not in {"A", "B", "C"}:
                return jsonify({"error": "grade must be A, B or C"}), 400
            batch.grade = data["grade"].upper()
        if "harvest_date" in data:
            batch.harvest_date = datetime.strptime(data["harvest_date"], "%Y-%m-%d").date()
        if "is_active" in data:
            batch.is_active = bool(data["is_active"])
        if "description" in data:
            batch.description = (data.get("description") or "").strip() or None
        audit("batch_update", batch.batch_id)
        db.session.commit()
        return jsonify({"message": "category updated", "batch": batch.to_dict(),
                        "price_alerts_fired": fired})
    except ValueError:
        return jsonify({"error": "invalid numeric/date value"}), 400


@bp.post("/batches/<int:pk>/image")
@role_required("admin")
def admin_upload_batch_image(pk):
    """Upload a jaggery photo for a batch (stored locally, served at /uploads/...)."""
    batch = db.session.get(JaggeryBatch, pk)
    if not batch:
        return jsonify({"error": "category not found"}), 404
    if "file" not in request.files:
        return jsonify({"error": "no file part named 'file'"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "empty filename"}), 400
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in Config.IMAGE_EXTENSIONS:
        return jsonify({"error": f"image must be one of: {', '.join(sorted(Config.IMAGE_EXTENSIONS))}"}), 400

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    safe = secure_filename(f"batch_{batch.batch_id}_{uuid.uuid4().hex[:8]}.{ext}")
    file.save(os.path.join(Config.UPLOAD_FOLDER, safe))
    batch.image_path = safe
    audit("batch_image", f"{batch.batch_id} -> {safe}")
    db.session.commit()
    return jsonify({"message": "image uploaded", "image_path": safe})


@bp.delete("/batches/<int:pk>/image")
@role_required("admin")
def admin_remove_batch_image(pk):
    batch = db.session.get(JaggeryBatch, pk)
    if not batch:
        return jsonify({"error": "category not found"}), 404
    batch.image_path = None
    db.session.commit()
    return jsonify({"message": "image removed"})


@bp.post("/batches/<int:pk>/images")
@role_required("admin")
def admin_add_batch_images(pk):
    """Add one or more extra photos to a batch (field 'files', multiple allowed)."""
    batch = db.session.get(JaggeryBatch, pk)
    if not batch:
        return jsonify({"error": "category not found"}), 404
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
            batch.image_path = name   # cover photo (kept only in image_path)
        else:
            db.session.add(BatchImage(batch_id=batch.id, image_path=name))  # extra photo
        saved.append(name)
    audit("batch_images_add", f"{batch.batch_id} +{len(saved)}")
    db.session.commit()
    return jsonify({"message": f"{len(saved)} image(s) added", "added": saved})


@bp.delete("/batches/<int:pk>/images/<int:img_id>")
@role_required("admin")
def admin_delete_batch_image(pk, img_id):
    img = db.session.get(BatchImage, img_id)
    if not img or img.batch_id != pk:
        return jsonify({"error": "image not found"}), 404
    batch = db.session.get(JaggeryBatch, pk)
    if batch and batch.image_path == img.image_path:
        batch.image_path = None
    db.session.delete(img)
    db.session.flush()
    if batch and not batch.image_path:   # promote next remaining photo to cover
        nxt = BatchImage.query.filter_by(batch_id=pk).first()
        batch.image_path = nxt.image_path if nxt else None
    db.session.commit()
    return jsonify({"message": "image removed"})


@bp.delete("/batches/<int:pk>")
@role_required("admin")
def admin_delete_batch(pk):
    """Admin removes a category: a soft delete, so order history stays intact.
    The product instantly disappears from the shop and from the owning
    warehouse's stock, and the warehouse is notified about the removal."""
    batch = db.session.get(JaggeryBatch, pk)
    if not batch or batch.deleted_at is not None:
        return jsonify({"error": "category not found"}), 404
    code = batch.batch_id
    batch.deleted_at = datetime.now(timezone.utc)
    batch.deleted_by = "admin"
    batch.delete_ack = True   # the admin's own deletion needs no admin-side alarm
    batch.is_active = False
    audit("batch_deleted_by_admin", f"{code} (WH#{batch.warehouse_id})")
    db.session.commit()
    return jsonify({"message": f"{code} deleted — removed from the shop and the warehouse has been notified"})
