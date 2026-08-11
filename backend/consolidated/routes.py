"""
HTTP layer for the consolidated pickup & delivery system.

Thin on purpose: authenticate, parse, call a service inside one transaction,
commit or roll back, serialise. All rules live in services.py.

    Customer   POST   /api/checkout
               POST   /api/orders/<id>/capture-payment
               GET    /api/orders/<id>/consolidated
    Warehouse  GET    /api/warehouse/sub-orders
               PATCH  /api/sub-orders/<id>/ready-for-pickup
               POST   /api/sub-orders/<id>/cancel
               GET    /api/warehouse/wallet
               POST   /api/warehouse/wallet/withdraw
    Rider      GET    /api/rider/tasks
               POST   /api/deliveries/<id>/stops/<stop_id>/arrive | collect | skip
               POST   /api/deliveries/<id>/complete
    Admin      GET    /api/admin/escrow
               POST   /api/admin/sub-orders/<id>/refund
               POST   /api/ops/prep-sla-sweep
               GET    /api/ops/settings
"""
from flask import Blueprint, request, jsonify, g

from db import db
from models import Order, User
from auth import role_required, audit

from .models import (SubOrder, Delivery, DeliveryStop, WarehouseWallet,
                     PayoutLedger, PlatformLedger, Refund)
from . import services as svc
from .services import BusinessError
from .settings import settings

bp = Blueprint("consolidated", __name__, url_prefix="/api")


# --------------------------------------------------------------- helpers
def _fail(exc):
    return jsonify({"error": exc.message}), exc.status


def _sub_order_or_404(sub_id):
    sub = db.session.get(SubOrder, sub_id)
    if not sub:
        raise BusinessError("sub-order not found", 404)
    return sub


def _my_order_or_404(order_id):
    order = Order.query.filter_by(id=order_id, customer_id=g.current_user.id).first()
    if not order:
        raise BusinessError("order not found", 404)
    return order


def _order_view(order):
    """Parent + children + trips in one payload — what every dashboard needs."""
    subs = sorted(order.sub_orders, key=lambda s: s.seq)
    charged = sum(round(float(s.customer_charged)) for s in subs)
    return {
        "order": order.to_dict(),
        "escrow_status": order.escrow_status,
        "refunded_total": round(float(order.refunded_total)),
        "charged_total": charged,
        "warehouse_count": len({s.warehouse_id for s in subs}),
        "sub_orders": [s.to_dict() for s in subs],
        "deliveries": [d.to_dict() for d in order.deliveries],
    }


# =====================================================================
# STEP 1 + 2 — single checkout across warehouses, split into sub-orders
# =====================================================================
@bp.post("/checkout")
@role_required("customer")
def checkout():
    """
    Body:
    {
      "items": [{"batch_pk": 1, "qty_kg": 5}, {"batch_pk": 9, "qty_kg": 2}],
      "delivery_address": "Ward 5, No. 23, Thiri Street",
      "location": "Yangon",              // city (local) or country (foreign)
      "delivery_scope": "local",
      "payment_method": "kpay",          // null = decide on the pay screen
      "pay_now": true,                   // simulate the gateway capturing at once
      "client_token": "uuid-v4"          // optional; makes retries idempotent
    }

    Response 201:
    { "order": {...}, "sub_orders": [ ... one per warehouse ... ], "deliveries": [] }
    """
    data = request.get_json(silent=True) or {}
    address = (data.get("delivery_address") or "").strip()
    location = (data.get("location") or data.get("pincode") or "").strip() or None
    if not address:
        return jsonify({"error": "delivery_address is required"}), 400

    try:
        # the customer's chosen city drives the ONE delivery fee for the trip
        from routes.customer import _delivery_charge_for
        scope = (data.get("delivery_scope") or "local").strip().lower()
        fee = _delivery_charge_for(location, scope)

        order, created = svc.create_consolidated_order(
            g.current_user,
            data.get("items") or [],
            delivery_address=address,
            location=location,
            delivery_scope=scope if scope in ("local", "foreign") else "local",
            delivery_fee=fee,
            preferred_date=None,
            payment_method=(data.get("payment_method") or None),
            client_token=(data.get("client_token") or None),
        )
        if created and data.get("pay_now"):
            # In production this runs from the gateway webhook, not the request
            # that started it — the service is idempotent either way.
            svc.capture_payment(order, method=data.get("payment_method"),
                                reference=data.get("payment_reference"),
                                actor_id=g.current_user.id)
        if created:
            audit("consolidated_checkout",
                  f"order {order.id}: {len(order.sub_orders)} sub-order(s)")
        db.session.commit()
    except BusinessError as exc:
        db.session.rollback()
        return _fail(exc)
    except Exception as exc:                      # noqa: BLE001 — clean rollback
        db.session.rollback()
        return jsonify({"error": f"checkout failed: {exc}"}), 500

    return jsonify(_order_view(order)), (201 if created else 200)


@bp.post("/orders/<int:order_id>/capture-payment")
@role_required("customer", "admin")
def capture_payment(order_id):
    """Payment confirmed → money sits in platform escrow, warehouses start packing."""
    try:
        order = (db.session.get(Order, order_id) if g.current_user.role == "admin"
                 else _my_order_or_404(order_id))
        if not order:
            raise BusinessError("order not found", 404)
        svc.capture_payment(order, method=(request.get_json(silent=True) or {}).get("method"),
                            reference=(request.get_json(silent=True) or {}).get("reference"),
                            actor_id=g.current_user.id)
        audit("escrow_hold", f"order {order.id}")
        db.session.commit()
    except BusinessError as exc:
        db.session.rollback()
        return _fail(exc)
    return jsonify(_order_view(order))


@bp.get("/orders/<int:order_id>/consolidated")
@role_required("customer", "admin")
def order_detail(order_id):
    """Customer/admin view: the parent, its sub-orders and the trip(s)."""
    try:
        order = (db.session.get(Order, order_id) if g.current_user.role == "admin"
                 else _my_order_or_404(order_id))
        if not order:
            raise BusinessError("order not found", 404)
    except BusinessError as exc:
        return _fail(exc)
    return jsonify(_order_view(order))


# =====================================================================
# STEP 3 — warehouse sees ONLY its own sub-orders and marks them ready
# =====================================================================
@bp.get("/warehouse/sub-orders")
@role_required("warehouse", "admin")
def my_sub_orders():
    """
    Isolated notification list. A warehouse account can only ever see rows for
    its own warehouse_id — there is no parameter that widens that.
    """
    q = SubOrder.query
    if g.current_user.role == "warehouse":
        if not g.current_user.warehouse_id:
            return jsonify([])
        q = q.filter(SubOrder.warehouse_id == g.current_user.warehouse_id)
    elif request.args.get("warehouse_id", type=int):
        q = q.filter(SubOrder.warehouse_id == request.args.get("warehouse_id", type=int))

    status = (request.args.get("status") or "").strip()
    if status:
        q = q.filter(SubOrder.status == status)
    elif request.args.get("open") == "1":
        q = q.filter(SubOrder.status.in_(SubOrder.OPEN_STATES))

    rows = q.order_by(SubOrder.created_at.desc()).limit(200).all()
    out = []
    for s in rows:
        d = s.to_dict()
        # what the warehouse needs to pack, without leaking the customer's
        # other warehouses' contents
        d["delivery_location"] = s.order.pincode if s.order else None
        d["paid"] = bool(s.order and s.order.payment_status == "paid")
        out.append(d)
    return jsonify(out)


@bp.patch("/sub-orders/<int:sub_id>/ready-for-pickup")
@role_required("warehouse", "admin")
def ready_for_pickup(sub_id):
    """
    STEP 3 → STEP 4 bridge.

    Marks this warehouse's sub-order ready, then asks the dispatcher whether the
    consolidated trip can now go out. The trip is created only when EVERY open
    sub-order of the parent is ready; otherwise this simply records readiness.

    Response tells the warehouse exactly what happened:
    { "sub_order": {...}, "dispatched": true, "delivery": {...},
      "waiting_on": ["ORD-1001-C"] }
    """
    try:
        sub = _sub_order_or_404(sub_id)
        changed = svc.mark_ready_for_pickup(sub, g.current_user)
        trip = svc.try_dispatch(sub.order, actor_id=g.current_user.id)
        if changed:
            audit("sub_order_ready", sub.sub_order_no)
        db.session.commit()
    except BusinessError as exc:
        db.session.rollback()
        return _fail(exc)

    waiting = [s.sub_order_no for s in sub.order.sub_orders
               if s.is_open and s.status != "ready_for_pickup"]
    return jsonify({
        "sub_order": sub.to_dict(),
        "changed": changed,
        "dispatched": trip is not None,
        "delivery": trip.to_dict() if trip else None,
        "waiting_on": waiting,
    })


@bp.post("/sub-orders/<int:sub_id>/cancel")
@role_required("warehouse", "admin")
def cancel_sub_order(sub_id):
    """
    EDGE CASE 1 — out of stock / warehouse cancels.
    Restocks, reverses that warehouse's pending credit, refunds the customer's
    slice, drops the stop from the route, and lets the siblings carry on.
    """
    data = request.get_json(silent=True) or {}
    try:
        sub = _sub_order_or_404(sub_id)
        refund = svc.cancel_sub_order(sub, g.current_user,
                                      data.get("reason") or "out of stock",
                                      refund=data.get("refund", True))
        audit("sub_order_cancelled", f"{sub.sub_order_no}: {sub.cancel_reason}")
        db.session.commit()
    except BusinessError as exc:
        db.session.rollback()
        return _fail(exc)
    return jsonify({
        "sub_order": sub.to_dict(),
        "refund": refund.to_dict() if refund else None,
        "parent": _order_view(sub.order),
    })


# =====================================================================
# STEP 4 — rider drives the route
# =====================================================================
@bp.get("/rider/tasks")
@role_required("rider", "admin")
def rider_tasks():
    """The rider's assigned trips, each with its stops in visiting order."""
    q = Delivery.query
    if g.current_user.role == "rider":
        q = q.filter(Delivery.rider_id == g.current_user.id)
    if request.args.get("active", "1") == "1":
        q = q.filter(Delivery.status.in_(Delivery.ACTIVE_STATES))
    trips = q.order_by(Delivery.created_at.desc()).limit(100).all()
    return jsonify([t.to_dict() for t in trips])


def _stop_action(delivery_id, stop_id, action):
    stop = db.session.get(DeliveryStop, stop_id)
    if not stop or stop.delivery_id != delivery_id:
        raise BusinessError("stop not found on this trip", 404)
    data = request.get_json(silent=True) or {}
    if action == "arrive":
        svc.collect_stop(stop, g.current_user, arrived_only=True)
    elif action == "collect":
        svc.collect_stop(stop, g.current_user)
    else:
        svc.skip_stop(stop, g.current_user, data.get("reason"))
    return stop


@bp.post("/deliveries/<int:delivery_id>/stops/<int:stop_id>/arrive")
@role_required("rider", "admin")
def stop_arrive(delivery_id, stop_id):
    try:
        stop = _stop_action(delivery_id, stop_id, "arrive")
        db.session.commit()
    except BusinessError as exc:
        db.session.rollback()
        return _fail(exc)
    return jsonify(stop.delivery.to_dict())


@bp.post("/deliveries/<int:delivery_id>/stops/<int:stop_id>/collect")
@role_required("rider", "admin")
def stop_collect(delivery_id, stop_id):
    """Goods picked up at this warehouse; sub-order → picked_up."""
    try:
        stop = _stop_action(delivery_id, stop_id, "collect")
        audit("pickup_collected", stop.sub_order.sub_order_no)
        db.session.commit()
    except BusinessError as exc:
        db.session.rollback()
        return _fail(exc)
    return jsonify(stop.delivery.to_dict())


@bp.post("/deliveries/<int:delivery_id>/stops/<int:stop_id>/skip")
@role_required("rider", "admin")
def stop_skip(delivery_id, stop_id):
    """
    EDGE CASE 3 (rider side) — warehouse still not packed when the rider arrives.
    The trip continues; this sub-order returns to the pool for a follow-up trip.
    """
    try:
        stop = _stop_action(delivery_id, stop_id, "skip")
        delivery = stop.delivery
        audit("pickup_skipped", f"delivery {delivery.id}")
        db.session.commit()
    except BusinessError as exc:
        db.session.rollback()
        return _fail(exc)
    return jsonify(delivery.to_dict())


# =====================================================================
# STEP 5 — delivered → commission taken, wallets released
# =====================================================================
@bp.post("/deliveries/<int:delivery_id>/complete")
@role_required("rider", "admin")
def complete_delivery(delivery_id):
    """
    Body: { "otp": "123456", "note": "handed to customer" }

    Marks the consolidated delivery complete and settles every warehouse on the
    trip: pending → available, commission recognised, escrow released.
    Idempotent — a retried call returns the same state and pays nobody twice.
    """
    data = request.get_json(silent=True) or {}
    delivery = db.session.get(Delivery, delivery_id)
    if not delivery:
        return jsonify({"error": "delivery not found"}), 404
    try:
        changed = svc.complete_delivery(delivery, g.current_user,
                                        otp=data.get("otp"), note=data.get("note"))
        if changed:
            audit("delivery_completed", f"trip {delivery.task_no}")
        db.session.commit()
    except BusinessError as exc:
        db.session.rollback()
        return _fail(exc)

    wallets = [w.to_dict() for w in WarehouseWallet.query.filter(
        WarehouseWallet.warehouse_id.in_(
            [s.warehouse_id for s in delivery.stops])).all()]
    return jsonify({
        "changed": changed,
        "delivery": delivery.to_dict(),
        "parent": _order_view(delivery.order),
        "wallets": wallets,
    })


# =====================================================================
# Wallets & payouts
# =====================================================================
@bp.get("/warehouse/wallet")
@role_required("warehouse", "admin")
def wallet_view():
    wid = (g.current_user.warehouse_id if g.current_user.role == "warehouse"
           else request.args.get("warehouse_id", type=int))
    if not wid:
        return jsonify({"error": "warehouse_id required"}), 400
    wallet = WarehouseWallet.query.filter_by(warehouse_id=wid).first()
    ledger = (PayoutLedger.query.filter_by(warehouse_id=wid)
              .order_by(PayoutLedger.id.desc()).limit(100).all())
    return jsonify({
        "wallet": wallet.to_dict() if wallet else {
            "warehouse_id": wid, "pending_balance": 0, "available_balance": 0,
            "withdrawn_total": 0, "lifetime_earned": 0},
        "ledger": [e.to_dict() for e in ledger],
    })


@bp.post("/warehouse/wallet/withdraw")
@role_required("warehouse", "admin")
def wallet_withdraw():
    data = request.get_json(silent=True) or {}
    wid = (g.current_user.warehouse_id if g.current_user.role == "warehouse"
           else data.get("warehouse_id"))
    try:
        if not wid:
            raise BusinessError("warehouse_id required", 400)
        wallet = svc.withdraw(int(wid), data.get("amount"), g.current_user,
                              reference=data.get("reference"))
        audit("wallet_withdrawal", f"warehouse {wid}: {data.get('amount')} Kyats")
        db.session.commit()
    except BusinessError as exc:
        db.session.rollback()
        return _fail(exc)
    return jsonify(wallet.to_dict())


# =====================================================================
# Platform / Super Admin
# =====================================================================
@bp.get("/admin/escrow")
@role_required("admin")
def escrow_overview():
    """Money currently held, commission earned, and what is owed to warehouses."""
    from sqlalchemy import func as f
    held = db.session.query(f.coalesce(f.sum(PlatformLedger.escrow_delta), 0)).scalar()
    commission = db.session.query(f.coalesce(f.sum(PlatformLedger.amount), 0)) \
        .filter(PlatformLedger.entry_type == "commission_earned").scalar()
    refunded = db.session.query(f.coalesce(f.sum(PlatformLedger.amount), 0)) \
        .filter(PlatformLedger.entry_type == "refund_out").scalar()
    pending = db.session.query(f.coalesce(f.sum(WarehouseWallet.pending_balance), 0)).scalar()
    available = db.session.query(f.coalesce(f.sum(WarehouseWallet.available_balance), 0)).scalar()
    return jsonify({
        "escrow_balance": round(float(held)),
        "commission_earned": round(float(commission)),
        "refunded_total": round(float(refunded)),
        "warehouse_pending_total": round(float(pending)),
        "warehouse_available_total": round(float(available)),
        "wallets": [w.to_dict() for w in WarehouseWallet.query.all()],
        "recent": [e.to_dict() for e in PlatformLedger.query
                   .order_by(PlatformLedger.id.desc()).limit(50).all()],
    })


@bp.post("/admin/sub-orders/<int:sub_id>/refund")
@role_required("admin")
def refund_sub_order(sub_id):
    """
    EDGE CASE 2 — partial refund on one sub-order.
    Body: { "amount": 4000, "reason": "1kg short" }
    Siblings and the parent order are untouched.
    """
    data = request.get_json(silent=True) or {}
    try:
        sub = _sub_order_or_404(sub_id)
        row = svc.process_refund(sub, data.get("amount"), g.current_user,
                                 reason=data.get("reason"))
        audit("sub_order_refund", f"{sub.sub_order_no}: {data.get('amount')} Kyats")
        db.session.commit()
    except BusinessError as exc:
        db.session.rollback()
        return _fail(exc)
    return jsonify({"refund": row.to_dict() if row else None,
                    "sub_order": sub.to_dict()})


@bp.get("/admin/orders/<int:order_id>/refunds")
@role_required("admin")
def order_refunds(order_id):
    rows = Refund.query.filter_by(order_id=order_id).order_by(Refund.id).all()
    return jsonify([r.to_dict() for r in rows])


# =====================================================================
# Ops — SLA sweep (cron) + effective settings
# =====================================================================
@bp.post("/ops/prep-sla-sweep")
@role_required("admin")
def prep_sla_sweep():
    """
    EDGE CASE 3 — the slow-warehouse sweep. Point a scheduler at this every few
    minutes. Nudges late warehouses, dispatches partial trips past the grace
    window, and auto-cancels past the hard deadline.
    """
    try:
        report = svc.sweep_prep_slas(g.current_user)
        db.session.commit()
    except BusinessError as exc:
        db.session.rollback()
        return _fail(exc)
    return jsonify(report)


@bp.get("/ops/settings")
@role_required("admin")
def ops_settings():
    return jsonify(settings.as_dict())


@bp.get("/ops/riders")
@role_required("admin")
def list_riders():
    from .models import RiderProfile
    rows = (db.session.query(RiderProfile).join(User, User.id == RiderProfile.user_id)
            .filter(User.role == "rider").all())
    return jsonify([r.to_dict() for r in rows])
