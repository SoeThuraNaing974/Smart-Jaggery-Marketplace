"""
Business logic for the consolidated pickup & delivery flow.

Every function here is written to be called inside ONE database transaction and
to be safe to retry. Two techniques do the heavy lifting:

* **Row locks in a fixed order.** Batches are locked by ascending id and wallets
  by ascending warehouse_id, so two concurrent checkouts / settlements can never
  deadlock by grabbing the same rows in opposite orders.

* **Idempotency keys on money.** Every wallet or escrow movement carries a
  deterministic key (`release:sub_order:42`). A UNIQUE index rejects the second
  attempt, so a retried request cannot pay a warehouse twice.

Routes own the commit/rollback; services raise `BusinessError` for anything the
caller should turn into a 4xx.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import random
import string

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from db import db
from models import Order, OrderItem, JaggeryBatch, User, Warehouse
from services import price_order

from .models import (SubOrder, Delivery, DeliveryStop, WarehouseWallet,
                     PayoutLedger, PlatformLedger, Refund, RiderProfile)
from .money import split_order_money, assert_balanced, to_kyats
from .settings import settings


class BusinessError(Exception):
    """A rule was broken. `status` is the HTTP code the route should return."""

    def __init__(self, message, status=422):
        super().__init__(message)
        self.message = message
        self.status = status


# =====================================================================
# Step 1 + 2 — single checkout → parent order → child sub-orders
# =====================================================================
def _lock_batches(item_specs):
    """
    Load and lock every requested batch, ALWAYS in ascending id order.
    Returns {batch_pk: JaggeryBatch}. Consistent lock ordering = no deadlocks
    when two customers buy overlapping baskets at the same moment.
    """
    ids = sorted({int(i["batch_pk"]) for i in item_specs})
    rows = (JaggeryBatch.query
            .filter(JaggeryBatch.id.in_(ids))
            .order_by(JaggeryBatch.id)
            .with_for_update()
            .all())
    return {b.id: b for b in rows}


def _validate_and_group(item_specs):
    """
    Turn raw cart lines into per-warehouse groups, rejecting anything unsellable.
    Returns (groups, line_items, total_qty) where groups is
    {warehouse_id: {"goods_subtotal": int, "lines": [...]}}
    """
    if not item_specs:
        raise BusinessError("cart is empty", 400)

    batches = _lock_batches(item_specs)

    # merge duplicate lines for the same batch so stock checks see the true qty
    wanted = {}
    for spec in item_specs:
        pk = int(spec.get("batch_pk") or 0)
        qty = float(spec.get("qty_kg") or 0)
        if qty <= 0:
            raise BusinessError("qty_kg must be positive", 400)
        wanted[pk] = wanted.get(pk, 0.0) + qty

    groups, line_items, total_qty = {}, [], 0.0
    for pk, qty in wanted.items():
        batch = batches.get(pk)
        if not batch or batch.deleted_at is not None:
            raise BusinessError(f"product {pk} is no longer available", 404)
        if batch.is_expired:
            raise BusinessError(f"{batch.batch_id} is EXPIRED and cannot be ordered")
        if not batch.is_active:
            raise BusinessError(f"{batch.batch_id} is not available")
        if float(batch.qty_kg) < qty:
            raise BusinessError(
                f"insufficient stock for {batch.batch_id}: "
                f"{float(batch.qty_kg)}kg available, {qty}kg requested")

        unit = float(batch.price_per_kg)
        line_total = to_kyats(unit * qty)
        line = {"batch": batch, "qty": qty, "unit": unit, "line_total": line_total}
        line_items.append(line)
        total_qty += qty

        g = groups.setdefault(batch.warehouse_id, {"goods_subtotal": 0, "lines": []})
        g["goods_subtotal"] += line_total
        g["lines"].append(line)

    return groups, line_items, total_qty


def _sub_order_no(order_id, seq):
    """ORD-1001-A, -B, -C … readable for warehouse staff and support."""
    suffix = string.ascii_uppercase[seq - 1] if seq <= 26 else str(seq)
    return f"ORD-{order_id}-{suffix}"


def create_consolidated_order(customer, item_specs, *, delivery_address, location,
                              delivery_scope="local", delivery_fee=None,
                              preferred_date=None, payment_method=None,
                              client_token=None):
    """
    STEP 1 & 2 of the flow.

    One cart spanning N warehouses becomes:
        1 parent Order   (the customer's single payment)
        N SubOrders      (one per warehouse, money already split)
        M OrderItems     (each linked to its parent AND its sub-order)

    Stock is decremented here, at checkout, so two customers cannot both buy the
    last 5kg. Money is NOT moved yet — that happens in `capture_payment`.
    """
    # ---- idempotent retry: same token → return the order we already made ----
    if client_token:
        existing = Order.query.filter_by(client_token=client_token,
                                         customer_id=customer.id).first()
        if existing:
            return existing, False

    groups, line_items, total_qty = _validate_and_group(item_specs)

    # goods pricing + cart-wide promotion reuse the existing rules
    goods_subtotal, discount, _goods_net, promo = price_order(line_items, total_qty)
    goods_subtotal, discount = to_kyats(goods_subtotal), to_kyats(discount)

    fee = to_kyats(delivery_fee if delivery_fee is not None
                   else settings.default_delivery_fee())

    # ---- split the money across warehouses (integer Kyats, nothing lost) ----
    ordered_wh = sorted(groups.keys())          # deterministic sub-order lettering
    rates = {w.id: w.commission_rate for w in
             Warehouse.query.filter(Warehouse.id.in_(ordered_wh)).all()}
    parts = split_order_money(
        [{"warehouse_id": w,
          "goods_subtotal": groups[w]["goods_subtotal"],
          "rate": rates.get(w)} for w in ordered_wh],
        discount_total=discount,
        delivery_total=fee,
        default_rate=settings.commission_rate(),
        commission_on_delivery=settings.commission_on_delivery(),
    )
    assert_balanced(parts, goods_subtotal, discount, fee)

    # ---- parent order ----
    customer.order_count = (customer.order_count or 0) + 1
    order = Order(
        customer_id=customer.id,
        status="pending",                       # unpaid until capture_payment
        customer_seq=customer.order_count,
        delivery_address=delivery_address,
        pincode=location,
        delivery_scope=delivery_scope,
        preferred_date=preferred_date,
        subtotal=goods_subtotal,
        discount_amount=discount,
        delivery_charge=fee,
        total_price=goods_subtotal - discount,
        fulfillment="delivery",
        payment_method=payment_method,
        payment_status="unpaid",
        escrow_status="none",
        promotion_id=promo.id if promo else None,
        client_token=client_token,
        # legacy single-warehouse column: point at the biggest supplier so old
        # screens still show something sensible
        assigned_warehouse_id=max(ordered_wh, key=lambda w: groups[w]["goods_subtotal"]),
    )
    db.session.add(order)
    db.session.flush()                          # need order.id for sub-order numbers

    # ---- child sub-orders + items ----
    for seq, part in enumerate(parts, start=1):
        sub = SubOrder(
            order_id=order.id,
            warehouse_id=part.warehouse_id,
            sub_order_no=_sub_order_no(order.id, seq),
            seq=seq,
            status="pending",
            goods_subtotal=part.goods_subtotal,
            discount_share=part.discount_share,
            delivery_share=part.delivery_share,
            customer_charged=part.customer_charged,
            commission_rate=part.commission_rate,
            commission_amount=part.commission_amount,
            net_payout=part.net_payout,
        )
        db.session.add(sub)
        db.session.flush()

        for line in groups[part.warehouse_id]["lines"]:
            db.session.add(OrderItem(
                order_id=order.id,            # parent link (kept for old queries)
                sub_order_id=sub.id,          # child link (new)
                batch_pk=line["batch"].id,
                qty_kg=line["qty"],
                unit_price=line["unit"],
                line_total=line["line_total"],
            ))
            line["batch"].qty_kg = float(line["batch"].qty_kg) - line["qty"]

    return order, True


# =====================================================================
# Payment → platform escrow (Step 1c) and wallet "pending" credit
# =====================================================================
def _insert_or_skip(row) -> bool:
    """
    Insert `row` inside a SAVEPOINT. Returns False if it collided with an existing
    unique key (i.e. this money movement was already recorded) — the outer
    transaction survives untouched either way.
    """
    try:
        with db.session.begin_nested():
            db.session.add(row)
            db.session.flush()
        return True
    except IntegrityError:
        return False


def _wallet_for(warehouse_id, lock=True):
    """Fetch (or create) a warehouse wallet, locked for update by default."""
    q = WarehouseWallet.query.filter_by(warehouse_id=warehouse_id)
    if lock:
        q = q.with_for_update()
    wallet = q.first()
    if not wallet:
        wallet = WarehouseWallet(warehouse_id=warehouse_id, pending_balance=0,
                                 available_balance=0)
        db.session.add(wallet)
        db.session.flush()
    return wallet


def _post_ledger(wallet, *, entry_type, amount, pending_delta, available_delta,
                 key, sub_order_id=None, note=None, actor_id=None):
    """
    Apply one movement to a wallet and journal it.

    Returns True if applied, False if this exact movement was already applied
    (duplicate idempotency key) — the caller can treat False as success.
    """
    amount = to_kyats(amount)
    pending_delta, available_delta = to_kyats(pending_delta), to_kyats(available_delta)

    new_pending = round(float(wallet.pending_balance)) + pending_delta
    new_available = round(float(wallet.available_balance)) + available_delta
    if new_pending < 0 or new_available < 0:
        raise BusinessError(
            f"wallet for warehouse {wallet.warehouse_id} would go negative "
            f"(pending {new_pending}, available {new_available})")

    entry = PayoutLedger(
        warehouse_id=wallet.warehouse_id, sub_order_id=sub_order_id,
        entry_type=entry_type, amount=amount,
        pending_delta=pending_delta, available_delta=available_delta,
        pending_after=new_pending, available_after=new_available,
        idempotency_key=key, note=note, created_by=actor_id,
    )
    # SAVEPOINT: if this exact movement was already applied, UNIQUE(idempotency_key)
    # raises and only THIS insert is undone. A plain session.rollback() here would
    # throw away the caller's whole transaction (the order, the other wallets…).
    if not _insert_or_skip(entry):
        return False                        # replay → nothing to do

    wallet.pending_balance = new_pending
    wallet.available_balance = new_available
    if pending_delta > 0:
        wallet.lifetime_earned = round(float(wallet.lifetime_earned)) + pending_delta
    if entry_type == "withdrawal":
        wallet.withdrawn_total = round(float(wallet.withdrawn_total)) + amount
    return True


def _post_platform(entry_type, amount, key, *, order_id=None, sub_order_id=None,
                   escrow_delta=0, note=None):
    entry = PlatformLedger(order_id=order_id, sub_order_id=sub_order_id,
                           entry_type=entry_type, amount=to_kyats(amount),
                           escrow_delta=to_kyats(escrow_delta),
                           idempotency_key=key, note=note)
    return _insert_or_skip(entry)


def capture_payment(order, *, method=None, reference=None, actor_id=None):
    """
    The customer's single payment lands in the PLATFORM ESCROW account, and each
    warehouse's net payout is credited to its **pending** balance.

    Pending means "earned but not yet withdrawable" — it only becomes available
    when the rider confirms delivery (`complete_delivery`).
    """
    if order.payment_status == "paid":
        return False                              # already captured; idempotent

    subs = [s for s in order.sub_orders if s.status != "cancelled"]
    if not subs:
        raise BusinessError("order has no active sub-orders to pay for")

    charged = sum(round(float(s.customer_charged)) for s in subs)
    order.payment_status = "paid"
    order.payment_method = method or order.payment_method
    order.payment_reference = reference or order.payment_reference
    order.escrow_status = "held"
    order.status = "waiting"                      # warehouses now prepare

    _post_platform("escrow_in", charged, f"escrow_in:order:{order.id}",
                   order_id=order.id, escrow_delta=charged,
                   note=f"customer payment for order {order.id}")

    deadline = datetime.utcnow() + timedelta(hours=settings.prep_window_hours())
    for sub in sorted(subs, key=lambda s: s.warehouse_id):    # stable lock order
        sub.status = "preparing"
        sub.prep_deadline_at = deadline
        wallet = _wallet_for(sub.warehouse_id)
        _post_ledger(wallet, entry_type="credit_pending",
                     amount=sub.net_payout, pending_delta=sub.net_payout,
                     available_delta=0, key=f"pending:sub_order:{sub.id}",
                     sub_order_id=sub.id, actor_id=actor_id,
                     note=f"{sub.sub_order_no} earned (held until delivery)")
    return True


# =====================================================================
# Step 3 — warehouse marks its sub-order Ready for Pickup
# =====================================================================
def mark_ready_for_pickup(sub_order, actor):
    """
    Warehouse-side transition. Guarded so a sub-order cannot jump states or be
    marked ready by a warehouse that does not own it.
    """
    if actor.role == "warehouse" and actor.warehouse_id != sub_order.warehouse_id:
        raise BusinessError("this sub-order belongs to another warehouse", 403)
    if sub_order.status == "ready_for_pickup":
        return False                              # idempotent
    if sub_order.status not in ("pending", "preparing"):
        raise BusinessError(f"cannot mark '{sub_order.status}' as ready for pickup")
    if sub_order.order.payment_status != "paid":
        raise BusinessError("customer payment is not confirmed yet")

    sub_order.status = "ready_for_pickup"
    sub_order.ready_at = datetime.utcnow()
    return True


# =====================================================================
# Step 4 — build the consolidated route and assign ONE rider
# =====================================================================
def plan_route(subs, customer_location):
    """
    Decide the visiting order for the pickup run.

    Deliberately simple and swappable: warehouses in the customer's own city are
    visited last (so the freshest goods travel least), otherwise by warehouse id
    for a stable, testable sequence. Replace the sort key with a real distance
    matrix (Google/OSRM) without touching anything else.
    """
    city = (customer_location or "").strip().lower()

    def key(sub):
        wh_city = ((sub.warehouse.pincode or sub.warehouse.location or "")
                   if sub.warehouse else "").strip().lower()
        same_city = 1 if (city and city in wh_city) else 0
        return (same_city, sub.warehouse_id)

    return sorted(subs, key=key)


def pick_rider(customer_location):
    """
    Least-loaded available rider, preferring one based in the delivery city.
    Returns a User or None (None → the trip waits as 'pending_assignment').
    """
    active_counts = dict(
        db.session.query(Delivery.rider_id, func.count(Delivery.id))
        .filter(Delivery.rider_id.isnot(None),
                Delivery.status.in_(Delivery.ACTIVE_STATES))
        .group_by(Delivery.rider_id).all())

    city = (customer_location or "").strip().lower()
    candidates = (db.session.query(User, RiderProfile)
                  .join(RiderProfile, RiderProfile.user_id == User.id)
                  .filter(User.role == "rider",
                          RiderProfile.is_available.is_(True))
                  .all())

    free = []
    for user, profile in candidates:
        if getattr(user, "is_blocked", False):
            continue
        load = active_counts.get(user.id, 0)
        if load >= (profile.max_active_tasks or 1):
            continue
        local = 0 if (city and city == (profile.base_city or "").strip().lower()) else 1
        free.append((local, load, user.id, user))

    if not free:
        return None
    free.sort(key=lambda t: t[:3])
    return free[0][3]


def _new_task_no(order_id):
    n = Delivery.query.filter_by(order_id=order_id).count() + 1
    return f"TRIP-{order_id}-{n}"


def try_dispatch(order, *, partial=False, actor_id=None):
    """
    STEP 4 trigger. Creates the consolidated trip when every warehouse is ready
    (or, with `partial=True`, for whichever ones are ready now — see the rider
    delay strategy).

    Returns the Delivery, or None if it is not time yet.

    Concurrency: two warehouses can hit "Ready for Pickup" in the same
    millisecond. The parent order row is locked first, and
    UNIQUE(delivery_stops.sub_order_id) is the backstop — a second trip for the
    same goods cannot be committed.
    """
    db.session.query(Order).filter_by(id=order.id).with_for_update().first()

    open_subs = [s for s in order.sub_orders if s.is_open]
    if not open_subs:
        return None

    # already collected / on a trip? those are excluded by the unique stop index
    on_a_trip = {row.sub_order_id for row in
                 DeliveryStop.query.filter(
                     DeliveryStop.sub_order_id.in_([s.id for s in open_subs])).all()}
    waiting = [s for s in open_subs if s.id not in on_a_trip]
    if not waiting:
        return None

    ready = [s for s in waiting if s.status == "ready_for_pickup"]
    if not ready:
        return None
    if not partial and len(ready) != len(waiting):
        return None                     # STILL WAITING on a warehouse — no trip yet

    route = plan_route(ready, order.pincode)
    rider = pick_rider(order.pincode)

    delivery = Delivery(
        order_id=order.id,
        rider_id=rider.id if rider else None,
        task_no=_new_task_no(order.id),
        status="assigned" if rider else "pending_assignment",
        is_partial=partial and len(ready) != len(waiting),
        stop_count=len(route),
        # the fee follows the goods actually on this trip
        delivery_fee=sum(round(float(s.delivery_share)) for s in route),
        drop_address=order.delivery_address,
        drop_location=order.pincode,
        proof_otp="".join(random.choices(string.digits, k=6)),
        assigned_at=datetime.utcnow() if rider else None,
    )
    db.session.add(delivery)
    db.session.flush()

    for seq, sub in enumerate(route, start=1):
        db.session.add(DeliveryStop(
            delivery_id=delivery.id, sub_order_id=sub.id,
            warehouse_id=sub.warehouse_id, stop_seq=seq, status="pending"))

    if rider:
        order.status = "assigned"
    return delivery


# =====================================================================
# Rider progress: arrive → collect at each stop → deliver
# =====================================================================
def collect_stop(stop, actor, *, arrived_only=False):
    """Rider picked the goods up at one warehouse."""
    delivery = stop.delivery
    if actor.role == "rider" and delivery.rider_id != actor.id:
        raise BusinessError("this trip belongs to another rider", 403)
    if delivery.status in ("delivered", "cancelled", "failed"):
        raise BusinessError(f"trip is already {delivery.status}")

    now = datetime.utcnow()
    if arrived_only:
        if stop.status == "pending":
            stop.status, stop.arrived_at = "arrived", now
        return delivery

    if stop.status == "collected":
        return delivery                             # idempotent
    if stop.sub_order.status == "cancelled":
        raise BusinessError("this sub-order was cancelled — skip the stop instead")

    stop.status, stop.collected_at = "collected", now
    stop.arrived_at = stop.arrived_at or now
    stop.sub_order.status = "picked_up"
    stop.sub_order.picked_up_at = now
    if delivery.status in ("assigned", "pending_assignment"):
        delivery.status = "collecting"

    outstanding = [s for s in delivery.stops if s.status not in ("collected", "skipped")]
    if not outstanding:
        delivery.status = "out_for_delivery"
        delivery.collected_at = now
        delivery.order.status = "out_for_delivery"
    return delivery


def skip_stop(stop, actor, reason):
    """
    Warehouse was not ready when the rider arrived. The trip carries on with the
    rest instead of stalling; the skipped sub-order goes back to the pool and is
    dispatched on a follow-up trip.
    """
    delivery = stop.delivery
    if actor.role == "rider" and delivery.rider_id != actor.id:
        raise BusinessError("this trip belongs to another rider", 403)
    if stop.status == "collected":
        raise BusinessError("already collected — cannot skip")

    stop.status = "skipped"
    stop.skip_reason = (reason or "warehouse not ready")[:200]
    # back to 'preparing' so it can be re-dispatched later
    if stop.sub_order.status == "ready_for_pickup":
        stop.sub_order.status = "preparing"
        stop.sub_order.ready_at = None
    db.session.delete(stop)          # frees UNIQUE(sub_order_id) for the next trip
    delivery.is_partial = True
    delivery.stop_count = max(0, (delivery.stop_count or 1) - 1)

    remaining = [s for s in delivery.stops if s.id != stop.id]
    if remaining and all(s.status in ("collected", "skipped") for s in remaining):
        delivery.status = "out_for_delivery"
        delivery.collected_at = datetime.utcnow()
    return delivery


# =====================================================================
# Step 5 — delivered → release funds from pending to available
# =====================================================================
def complete_delivery(delivery, actor, *, otp=None, note=None):
    """
    The rider hands the consolidated package to the customer.

    Then, atomically:
      * every sub-order on this trip → delivered
      * each warehouse's net payout moves pending → **available** (withdrawable)
      * the platform recognises its commission as revenue and releases escrow
      * the parent order closes once no sub-order is still open

    Wallet movements use `release:sub_order:<id>` keys, so calling this endpoint
    twice cannot pay anyone twice.
    """
    if actor.role == "rider" and delivery.rider_id != actor.id:
        raise BusinessError("this trip belongs to another rider", 403)
    if delivery.status == "delivered":
        return False                                    # idempotent
    if delivery.status in ("cancelled", "failed"):
        raise BusinessError(f"trip is {delivery.status}")

    collected = [s for s in delivery.stops if s.status == "collected"]
    pending_stops = [s for s in delivery.stops if s.status == "pending"]
    if pending_stops:
        raise BusinessError(
            f"{len(pending_stops)} pickup(s) not collected yet — collect or skip them first")
    if not collected:
        raise BusinessError("nothing was collected on this trip")
    if settings.require_delivery_otp() and otp and delivery.proof_otp and \
            otp != delivery.proof_otp:
        raise BusinessError("delivery confirmation code does not match", 400)

    now = datetime.utcnow()
    delivery.status = "delivered"
    delivery.delivered_at = now
    delivery.proof_note = (note or "")[:200] or None

    order = delivery.order
    # ascending warehouse_id: same lock order as everywhere else
    for stop in sorted(collected, key=lambda s: s.warehouse_id):
        sub = stop.sub_order
        if sub.status == "delivered":
            continue
        sub.status = "delivered"
        sub.delivered_at = now

        payable = round(float(sub.net_payout)) - round(float(sub.refunded_amount))
        payable = max(0, payable)
        wallet = _wallet_for(sub.warehouse_id)
        _post_ledger(wallet, entry_type="release_available",
                     amount=payable, pending_delta=-payable, available_delta=payable,
                     key=f"release:sub_order:{sub.id}", sub_order_id=sub.id,
                     actor_id=actor.id,
                     note=f"{sub.sub_order_no} delivered — available to withdraw")
        _post_platform("commission_earned", sub.commission_amount,
                       f"commission:sub_order:{sub.id}", order_id=order.id,
                       sub_order_id=sub.id, escrow_delta=0,
                       note=f"{float(sub.commission_rate) * 100:.2f}% of {sub.sub_order_no}")
        _post_platform("payout_released", payable,
                       f"payout:sub_order:{sub.id}", order_id=order.id,
                       sub_order_id=sub.id, escrow_delta=-payable,
                       note=f"released to warehouse {sub.warehouse_id}")

    # close the parent only when nothing is still in flight
    still_open = [s for s in order.sub_orders if s.is_open]
    if not still_open:
        order.status = "delivered"
        order.delivered_at = now
        order.escrow_status = "released"
    return True


# =====================================================================
# Edge case 1 — partial cancellation (1 of N warehouses cannot supply)
# =====================================================================
def cancel_sub_order(sub_order, actor, reason, *, refund=True):
    """
    One warehouse drops out; the other sub-orders continue untouched.

    What happens, in order:
      1. stock goes back on the shelf for that warehouse's items
      2. its pending wallet credit is reversed (nothing was released yet)
      3. the customer is refunded that sub-order's share — goods AND its share
         of the delivery fee, since they received less service
      4. if it was already on a trip, the stop is dropped and the route resequenced
      5. if it was the LAST open sub-order, the parent order is cancelled
      6. otherwise dispatch is re-evaluated: the remaining warehouses may now all
         be ready, so the trip can go out immediately
    """
    if actor.role == "warehouse" and actor.warehouse_id != sub_order.warehouse_id:
        raise BusinessError("this sub-order belongs to another warehouse", 403)
    if sub_order.status == "cancelled":
        return None
    if sub_order.status in ("picked_up", "delivered"):
        raise BusinessError(
            "goods already left the warehouse — use a return/refund instead")

    order = sub_order.order
    now = datetime.utcnow()

    # 1) restock
    for item in sub_order.items:
        batch = db.session.query(JaggeryBatch).filter_by(id=item.batch_pk) \
            .with_for_update().first()
        if batch:
            batch.qty_kg = float(batch.qty_kg) + float(item.qty_kg)

    sub_order.status = "cancelled"
    sub_order.cancelled_at = now
    sub_order.cancel_reason = (reason or "cancelled by warehouse")[:200]

    # 2) reverse the pending credit (only if payment was captured)
    if order.payment_status == "paid":
        held = round(float(sub_order.net_payout)) - round(float(sub_order.refunded_amount))
        if held > 0:
            wallet = _wallet_for(sub_order.warehouse_id)
            _post_ledger(wallet, entry_type="reverse_pending",
                         amount=held, pending_delta=-held, available_delta=0,
                         key=f"reverse:sub_order:{sub_order.id}",
                         sub_order_id=sub_order.id, actor_id=actor.id,
                         note=f"{sub_order.sub_order_no} cancelled")

    # 3) refund the customer for this slice only
    refund_row = None
    if refund and order.payment_status == "paid":
        amount = sub_order.refundable_amount
        if not settings.refund_delivery_share_on_partial():
            amount = max(0, amount - round(float(sub_order.delivery_share)))
        if amount > 0:
            refund_row = process_refund(
                sub_order, amount, actor,
                reason=f"sub-order cancelled: {sub_order.cancel_reason}",
                key=f"refund:cancel:sub_order:{sub_order.id}")

    # 4) drop it from any planned trip
    stop = DeliveryStop.query.filter_by(sub_order_id=sub_order.id).first()
    if stop:
        delivery = stop.delivery
        db.session.delete(stop)
        db.session.flush()
        remaining = [s for s in delivery.stops if s.id != stop.id]
        delivery.stop_count = len(remaining)
        delivery.delivery_fee = round(float(delivery.delivery_fee)) - \
            round(float(sub_order.delivery_share))
        for seq, s in enumerate(sorted(remaining, key=lambda x: x.stop_seq), start=1):
            s.stop_seq = seq                              # resequence 1..n
        if not remaining:
            delivery.status = "cancelled"
            delivery.failed_reason = "all pickups cancelled"
        elif all(s.status in ("collected", "skipped") for s in remaining):
            delivery.status = "out_for_delivery"
            delivery.collected_at = delivery.collected_at or now

    # 5) whole order gone?
    if not [s for s in order.sub_orders if s.is_open]:
        if all(s.status == "cancelled" for s in order.sub_orders):
            order.status = "cancelled"
            order.escrow_status = "refunded"
        return refund_row

    # 6) the rest may now be ready to roll
    try_dispatch(order, actor_id=actor.id)
    return refund_row


# =====================================================================
# Edge case 2 — partial refund on ONE sub-order
# =====================================================================
def process_refund(sub_order, amount, actor, *, reason=None, key=None, method=None):
    """
    Refund `amount` Kyats against one sub-order without touching its siblings.

    Where the money comes from depends on whether it was already released:
      * not delivered yet → reverse from the warehouse's **pending** balance
      * already delivered → debit the warehouse's **available** balance
    The platform's escrow is reduced either way, and the parent order's
    refunded_total grows so invoices and reports stay truthful.
    """
    amount = to_kyats(amount)
    if amount <= 0:
        raise BusinessError("refund amount must be positive", 400)
    if amount > sub_order.refundable_amount:
        raise BusinessError(
            f"refund exceeds what is left on {sub_order.sub_order_no}: "
            f"{sub_order.refundable_amount} Kyats refundable", 400)

    order = sub_order.order
    if order.payment_status != "paid":
        raise BusinessError("nothing was captured for this order yet")

    seq = Refund.query.filter_by(sub_order_id=sub_order.id).count() + 1
    idem = key or f"refund:sub_order:{sub_order.id}:{seq}"

    kind = "full" if amount == sub_order.refundable_amount else "partial"
    row = Refund(order_id=order.id, sub_order_id=sub_order.id, amount=amount,
                 reason=(reason or "")[:200] or None,
                 kind=kind, status="processed", method=method or order.payment_method,
                 idempotency_key=idem, created_by=actor.id)
    if not _insert_or_skip(row):
        # same refund already processed (retry / double-click) → return the original
        return Refund.query.filter_by(idempotency_key=idem).first()

    # claw back the warehouse's share of what is being refunded
    already_released = sub_order.status == "delivered"
    net_share = min(amount, round(float(sub_order.net_payout)))
    if net_share > 0:
        wallet = _wallet_for(sub_order.warehouse_id)
        if already_released:
            _post_ledger(wallet, entry_type="debit_available",
                         amount=net_share, pending_delta=0, available_delta=-net_share,
                         key=f"refund_debit:{idem}", sub_order_id=sub_order.id,
                         actor_id=actor.id, note=f"refund on {sub_order.sub_order_no}")
        elif round(float(wallet.pending_balance)) > 0:
            take = min(net_share, round(float(wallet.pending_balance)))
            _post_ledger(wallet, entry_type="reverse_pending",
                         amount=take, pending_delta=-take, available_delta=0,
                         key=f"refund_reverse:{idem}", sub_order_id=sub_order.id,
                         actor_id=actor.id, note=f"refund on {sub_order.sub_order_no}")

    sub_order.refunded_amount = round(float(sub_order.refunded_amount)) + amount
    order.refunded_total = round(float(order.refunded_total)) + amount
    _post_platform("refund_out", amount, f"refund_out:{idem}", order_id=order.id,
                   sub_order_id=sub_order.id, escrow_delta=-amount,
                   note=row.reason)

    total_charged = sum(round(float(s.customer_charged)) for s in order.sub_orders)
    if round(float(order.refunded_total)) >= total_charged:
        order.escrow_status = "refunded"
    return row


# =====================================================================
# Edge case 3 — one warehouse is slow (rider delay strategy)
# =====================================================================
def evaluate_prep_sla(order, now=None):
    """
    Decide what to do about a parent order whose warehouses are not all ready.

    Returns one of:
      "wait"            — inside the SLA, nothing to do
      "nudge"           — past the deadline, remind the warehouse
      "dispatch_partial"— past deadline + grace, and someone IS ready:
                          send the rider with what exists, follow up later
      "auto_cancel"     — past the hard deadline: drop the late sub-order,
                          refund that slice, let the rest go
    """
    now = now or datetime.utcnow()
    open_subs = [s for s in order.sub_orders if s.is_open]
    late = [s for s in open_subs
            if s.status in ("pending", "preparing")
            and s.prep_deadline_at and s.prep_deadline_at < now]
    if not late:
        return "wait", []

    ready = [s for s in open_subs if s.status == "ready_for_pickup"]
    worst = min(s.prep_deadline_at for s in late)
    overdue_min = (now - worst).total_seconds() / 60.0

    if overdue_min >= settings.auto_cancel_after_minutes():
        return "auto_cancel", late
    if ready and overdue_min >= settings.partial_dispatch_after_minutes():
        return "dispatch_partial", late
    return "nudge", late


def sweep_prep_slas(actor, now=None):
    """
    Cron-friendly sweep over every paid, undelivered order. Call it from a
    scheduler (or POST /api/ops/prep-sla-sweep) every few minutes.
    """
    now = now or datetime.utcnow()
    orders = (Order.query
              .filter(Order.payment_status == "paid",
                      Order.status.notin_(("delivered", "cancelled")))
              .all())
    report = {"wait": 0, "nudge": [], "dispatch_partial": [], "auto_cancel": []}
    for order in orders:
        action, late = evaluate_prep_sla(order, now)
        if action == "wait":
            report["wait"] += 1
            continue
        if action == "nudge":
            report["nudge"].append({"order_id": order.id,
                                    "late": [s.sub_order_no for s in late]})
        elif action == "dispatch_partial":
            trip = try_dispatch(order, partial=True, actor_id=actor.id)
            report["dispatch_partial"].append({
                "order_id": order.id, "trip": trip.task_no if trip else None,
                "left_behind": [s.sub_order_no for s in late]})
        elif action == "auto_cancel":
            for sub in late:
                cancel_sub_order(sub, actor,
                                 "auto-cancelled: warehouse missed its preparation deadline")
            report["auto_cancel"].append({"order_id": order.id,
                                          "cancelled": [s.sub_order_no for s in late]})
    return report


# =====================================================================
# Withdrawals
# =====================================================================
def withdraw(warehouse_id, amount, actor, *, reference=None):
    """Move money out of a warehouse's available balance."""
    amount = to_kyats(amount)
    if amount <= 0:
        raise BusinessError("withdrawal amount must be positive", 400)
    wallet = _wallet_for(warehouse_id)
    if amount > round(float(wallet.available_balance)):
        raise BusinessError(
            f"insufficient available balance: {round(float(wallet.available_balance))} Kyats", 400)
    seq = PayoutLedger.query.filter_by(warehouse_id=warehouse_id,
                                       entry_type="withdrawal").count() + 1
    _post_ledger(wallet, entry_type="withdrawal", amount=amount,
                 pending_delta=0, available_delta=-amount,
                 key=f"withdraw:{warehouse_id}:{seq}", actor_id=actor.id,
                 note=reference or "withdrawal")
    return wallet
