"""
SQLAlchemy models for the consolidated pickup & delivery system.

Mirrors backend/schema_v28.sql. The existing `Order` stays the PARENT order —
it already owns the customer, the single payment and the invoice — so nothing
built on orders.id (invoices, messages, reviews) has to change.
"""
from datetime import datetime

from db import db

# BIGSERIAL on Postgres, plain INTEGER on SQLite — SQLite only auto-increments a
# column typed exactly INTEGER PRIMARY KEY, so a BigInteger PK would insert NULL
# and fail. Keeps the production type while the test suite runs on SQLite.
BigIntPK = db.BigInteger().with_variant(db.Integer, "sqlite")


class SubOrder(db.Model):
    """One warehouse's slice of a parent order: its own status and its own money."""
    __tablename__ = "sub_orders"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    sub_order_no = db.Column(db.String(32), nullable=False, unique=True)
    seq = db.Column(db.SmallInteger, nullable=False)

    # pending → preparing → ready_for_pickup → picked_up → delivered | cancelled
    status = db.Column(db.String(20), nullable=False, default="pending")

    goods_subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    discount_share = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    delivery_share = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    customer_charged = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    commission_rate = db.Column(db.Numeric(5, 4), nullable=False, default=0)
    commission_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    net_payout = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    refunded_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    prep_deadline_at = db.Column(db.DateTime)
    ready_at = db.Column(db.DateTime)
    picked_up_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    cancel_reason = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = db.relationship("Order", backref=db.backref("sub_orders", lazy="select",
                                                        cascade="all, delete-orphan"))
    warehouse = db.relationship("Warehouse")
    items = db.relationship("OrderItem", backref="sub_order", lazy="select")

    __table_args__ = (
        db.UniqueConstraint("order_id", "warehouse_id", name="uq_sub_order_wh"),
    )

    # ---- states that mean "the customer's money is still at risk here" ----
    OPEN_STATES = ("pending", "preparing", "ready_for_pickup", "picked_up")

    @property
    def is_open(self):
        return self.status in self.OPEN_STATES

    @property
    def refundable_amount(self):
        """What can still be refunded on this sub-order."""
        return max(0, round(float(self.customer_charged)) - round(float(self.refunded_amount)))

    def to_dict(self, with_items=True):
        d = {
            "id": self.id,
            "order_id": self.order_id,
            "sub_order_no": self.sub_order_no,
            "seq": self.seq,
            "warehouse_id": self.warehouse_id,
            "warehouse_name": self.warehouse.name if self.warehouse else None,
            "status": self.status,
            "goods_subtotal": round(float(self.goods_subtotal)),
            "discount_share": round(float(self.discount_share)),
            "delivery_share": round(float(self.delivery_share)),
            "customer_charged": round(float(self.customer_charged)),
            "commission_rate": float(self.commission_rate),
            "commission_amount": round(float(self.commission_amount)),
            "net_payout": round(float(self.net_payout)),
            "refunded_amount": round(float(self.refunded_amount)),
            "refundable_amount": self.refundable_amount,
            "prep_deadline_at": self.prep_deadline_at.isoformat() if self.prep_deadline_at else None,
            "ready_at": self.ready_at.isoformat() if self.ready_at else None,
            "picked_up_at": self.picked_up_at.isoformat() if self.picked_up_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "cancel_reason": self.cancel_reason,
        }
        if with_items:
            d["items"] = [{
                "batch_pk": it.batch_pk,
                "batch_id": it.batch.batch_id if it.batch else None,
                "qty_kg": float(it.qty_kg),
                "unit_price": round(float(it.unit_price)),
                "line_total": round(float(it.line_total)),
            } for it in self.items]
        return d


class Delivery(db.Model):
    """One consolidated trip: N warehouse pickups, then a single customer drop-off."""
    __tablename__ = "deliveries"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    task_no = db.Column(db.String(32), nullable=False, unique=True)
    status = db.Column(db.String(20), nullable=False, default="pending_assignment")
    is_partial = db.Column(db.Boolean, nullable=False, default=False)
    stop_count = db.Column(db.SmallInteger, nullable=False, default=0)
    delivery_fee = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    drop_address = db.Column(db.Text)
    drop_location = db.Column(db.String(60))
    proof_otp = db.Column(db.String(6))
    proof_note = db.Column(db.String(200))
    assigned_at = db.Column(db.DateTime)
    collected_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    failed_reason = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = db.relationship("Order", backref=db.backref("deliveries", lazy="select"))
    rider = db.relationship("User")
    stops = db.relationship("DeliveryStop", backref="delivery",
                            order_by="DeliveryStop.stop_seq",
                            cascade="all, delete-orphan")

    ACTIVE_STATES = ("pending_assignment", "assigned", "collecting",
                     "collected", "out_for_delivery")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "task_no": self.task_no,
            "status": self.status,
            "is_partial": self.is_partial,
            "rider_id": self.rider_id,
            "rider_name": self.rider.name if self.rider else None,
            "stop_count": self.stop_count,
            "delivery_fee": round(float(self.delivery_fee)),
            "drop_address": self.drop_address,
            "drop_location": self.drop_location,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "failed_reason": self.failed_reason,
            "stops": [s.to_dict() for s in self.stops],
        }


class DeliveryStop(db.Model):
    """One warehouse pickup inside a trip. UNIQUE(sub_order_id) app-wide:
    a sub-order can only ever be collected by one trip."""
    __tablename__ = "delivery_stops"

    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey("deliveries.id", ondelete="CASCADE"),
                            nullable=False)
    sub_order_id = db.Column(db.Integer, db.ForeignKey("sub_orders.id", ondelete="CASCADE"),
                             nullable=False, unique=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    stop_seq = db.Column(db.SmallInteger, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    arrived_at = db.Column(db.DateTime)
    collected_at = db.Column(db.DateTime)
    skip_reason = db.Column(db.String(200))

    sub_order = db.relationship("SubOrder")
    warehouse = db.relationship("Warehouse")

    __table_args__ = (db.UniqueConstraint("delivery_id", "stop_seq", name="uq_stop_seq"),)

    def to_dict(self):
        wh = self.warehouse
        return {
            "id": self.id,
            "stop_seq": self.stop_seq,
            "status": self.status,
            "sub_order_id": self.sub_order_id,
            "sub_order_no": self.sub_order.sub_order_no if self.sub_order else None,
            "warehouse_id": self.warehouse_id,
            "warehouse_name": wh.name if wh else None,
            "warehouse_location": wh.location if wh else None,
            "warehouse_phone": wh.phone if wh else None,
            "arrived_at": self.arrived_at.isoformat() if self.arrived_at else None,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "skip_reason": self.skip_reason,
        }


class WarehouseWallet(db.Model):
    """Cached projection of payout_ledgers. The ledger is the source of truth."""
    __tablename__ = "warehouse_wallets"

    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"),
                             nullable=False, unique=True)
    pending_balance = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    available_balance = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    withdrawn_total = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    lifetime_earned = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    warehouse = db.relationship("Warehouse")

    def to_dict(self):
        return {
            "warehouse_id": self.warehouse_id,
            "warehouse_name": self.warehouse.name if self.warehouse else None,
            "pending_balance": round(float(self.pending_balance)),
            "available_balance": round(float(self.available_balance)),
            "withdrawn_total": round(float(self.withdrawn_total)),
            "lifetime_earned": round(float(self.lifetime_earned)),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PayoutLedger(db.Model):
    """
    Append-only money journal for warehouses.

    `idempotency_key` is UNIQUE — that single index is what makes "release the
    funds" safe to call twice (a retried webhook, a double-clicked button, a
    replayed job). The second attempt hits a duplicate-key error, which the
    service layer swallows as "already applied".
    """
    __tablename__ = "payout_ledgers"

    id = db.Column(BigIntPK, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    sub_order_id = db.Column(db.Integer, db.ForeignKey("sub_orders.id"))
    entry_type = db.Column(db.String(24), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    pending_delta = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    available_delta = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    pending_after = db.Column(db.Numeric(14, 2), nullable=False)
    available_after = db.Column(db.Numeric(14, 2), nullable=False)
    idempotency_key = db.Column(db.String(120), nullable=False, unique=True)
    note = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "warehouse_id": self.warehouse_id,
            "sub_order_id": self.sub_order_id,
            "entry_type": self.entry_type,
            "amount": round(float(self.amount)),
            "pending_after": round(float(self.pending_after)),
            "available_after": round(float(self.available_after)),
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PlatformLedger(db.Model):
    """Escrow + commission journal for the Super Admin side of the house."""
    __tablename__ = "platform_ledgers"

    id = db.Column(BigIntPK, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    sub_order_id = db.Column(db.Integer, db.ForeignKey("sub_orders.id"))
    entry_type = db.Column(db.String(24), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    escrow_delta = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    idempotency_key = db.Column(db.String(120), nullable=False, unique=True)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "order_id": self.order_id, "sub_order_id": self.sub_order_id,
            "entry_type": self.entry_type, "amount": round(float(self.amount)),
            "escrow_delta": round(float(self.escrow_delta)), "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Refund(db.Model):
    """A refund against ONE sub-order (or the whole order when sub_order_id is NULL)."""
    __tablename__ = "refunds"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"),
                         nullable=False)
    sub_order_id = db.Column(db.Integer, db.ForeignKey("sub_orders.id"))
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    reason = db.Column(db.String(200))
    kind = db.Column(db.String(20), nullable=False, default="partial")
    status = db.Column(db.String(20), nullable=False, default="processed")
    method = db.Column(db.String(20))
    idempotency_key = db.Column(db.String(120), nullable=False, unique=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "order_id": self.order_id, "sub_order_id": self.sub_order_id,
            "amount": round(float(self.amount)), "reason": self.reason,
            "kind": self.kind, "status": self.status, "method": self.method,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RiderProfile(db.Model):
    """Extra rider fields; the login itself is a users row with role='rider'."""
    __tablename__ = "rider_profiles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        primary_key=True)
    vehicle_type = db.Column(db.String(20), nullable=False, default="motorbike")
    plate_no = db.Column(db.String(30))
    base_city = db.Column(db.String(60))
    is_available = db.Column(db.Boolean, nullable=False, default=True)
    max_active_tasks = db.Column(db.SmallInteger, nullable=False, default=1)
    rating = db.Column(db.Numeric(3, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.user.name if self.user else None,
            "phone": self.user.phone if self.user else None,
            "vehicle_type": self.vehicle_type, "plate_no": self.plate_no,
            "base_city": self.base_city, "is_available": self.is_available,
            "max_active_tasks": self.max_active_tasks,
            "rating": float(self.rating) if self.rating is not None else None,
        }
