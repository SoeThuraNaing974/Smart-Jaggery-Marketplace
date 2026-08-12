from datetime import datetime, date, timezone
from dateutil.relativedelta import relativedelta

from db import db


def _block_active(blocked, blocked_until):
    """A block is active if the flag is set AND (no time limit OR the limit hasn't passed)."""
    if not blocked:
        return False
    if blocked_until is None:
        return True
    bu = blocked_until if blocked_until.tzinfo else blocked_until.replace(tzinfo=timezone.utc)
    return bu > datetime.now(timezone.utc)


class Warehouse(db.Model):
    __tablename__ = "warehouses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(30))
    pincode = db.Column(db.String(12))
    email = db.Column(db.String(160))
    manager_name = db.Column(db.String(120))
    blocked = db.Column(db.Boolean, nullable=False, default=False)   # admin "Block" = staff locked out, data kept
    blocked_until = db.Column(db.DateTime(timezone=True))            # NULL = no limit; else auto-expires
    # Platform commission for this warehouse (0.0500 = 5%). NULL = platform default.
    commission_rate = db.Column(db.Numeric(5, 4))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    batches = db.relationship("JaggeryBatch", backref="warehouse", cascade="all, delete-orphan")

    def _own_block_active(self):
        return _block_active(self.blocked, self.blocked_until)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "phone": self.phone,
            "pincode": self.pincode,
            "email": self.email,
            "manager_name": self.manager_name,
            "blocked": self._own_block_active(),
            "blocked_until": self.blocked_until.isoformat() if self.blocked_until else None,
            "commission_rate": (float(self.commission_rate)
                                if self.commission_rate is not None else None),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    payment_pin_hash = db.Column(db.String(255))  # numeric PIN for confirming payments
    pin_reset_code = db.Column(db.String(255))     # hashed emailed OTP for PIN reset
    pin_reset_expires = db.Column(db.DateTime)
    pay_otp_hash = db.Column(db.String(255))       # hashed emailed OTP to confirm a payment
    pay_otp_expires = db.Column(db.DateTime)
    # 'customer' | 'warehouse' | 'admin'
    role = db.Column(db.String(20), nullable=False, default="customer", index=True)
    phone = db.Column(db.String(30))
    address = db.Column(db.Text)
    pincode = db.Column(db.String(60), index=True)  # delivery location: MM city or foreign country
    avatar_path = db.Column(db.String(255))  # profile picture filename in uploads/
    order_count = db.Column(db.Integer, nullable=False, default=0)  # monotonic per-customer order counter
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="SET NULL"))
    last_login = db.Column(db.DateTime(timezone=True))   # last login / page activity (for Active status)
    blocked = db.Column(db.Boolean, nullable=False, default=False)   # admin "Block" = locked out, data kept
    blocked_until = db.Column(db.DateTime(timezone=True))            # NULL = no limit; else auto-expires
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    warehouse = db.relationship("Warehouse")

    def _own_block_active(self):
        """This user's own block, honoring an optional time limit (auto-expires)."""
        return _block_active(self.blocked, self.blocked_until)

    @property
    def is_blocked(self):
        """Effective block: the user's own block OR (for staff) their warehouse's."""
        if self._own_block_active():
            return True
        if self.role == "warehouse" and self.warehouse is not None:
            return self.warehouse._own_block_active()
        return False

    @property
    def effective_blocked_until(self):
        """The end time of whichever block is in effect (own or the staff's warehouse)."""
        if self._own_block_active():
            return self.blocked_until
        if self.role == "warehouse" and self.warehouse is not None and self.warehouse._own_block_active():
            return self.warehouse.blocked_until
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "phone": self.phone,
            "address": self.address,
            "pincode": self.pincode,
            "avatar_path": self.avatar_path,
            "warehouse_id": self.warehouse_id,
            "blocked": self._own_block_active(),
            "blocked_until": self.blocked_until.isoformat() if self.blocked_until else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class JaggeryBatch(db.Model):
    __tablename__ = "jaggery_batches"

    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    # the category NAME shown everywhere — the same name may be reused freely
    # (products are identified by id); indexed for lookups only
    batch_id = db.Column(db.String(60), nullable=False, index=True)
    grade = db.Column(db.String(1), nullable=False)  # 'A' | 'B' | 'C'
    qty_kg = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    harvest_date = db.Column(db.Date, nullable=False)
    price_per_kg = db.Column(db.Numeric(10, 2), nullable=False)
    certificate_path = db.Column(db.String(255))
    image_path = db.Column(db.String(255))
    description = db.Column(db.Text)  # ingredients & effectiveness
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    deleted_at = db.Column(db.DateTime(timezone=True))   # set when the stock is soft-deleted
    delete_ack = db.Column(db.Boolean, nullable=False, default=False)  # admin acknowledged the deletion
    deleted_by = db.Column(db.String(10))  # 'warehouse' | 'admin' — which side deleted it
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # extra photos (the cover stays in image_path); deleted with the batch
    images = db.relationship("BatchImage", backref="batch",
                             cascade="all, delete-orphan", order_by="BatchImage.id")

    @property
    def is_expired(self):
        """harvest > EXPIRY_MONTHS (9) old => EXPIRED, cannot order."""
        from config import Config
        cutoff = date.today() - relativedelta(months=Config.EXPIRY_MONTHS)
        return self.harvest_date < cutoff

    @property
    def is_near_expiry(self):
        """harvest between NEAR_EXPIRY (8) and EXPIRY (9) months => warn, still orderable."""
        from config import Config
        near = date.today() - relativedelta(months=Config.NEAR_EXPIRY_MONTHS)
        return (not self.is_expired) and self.harvest_date < near

    @property
    def expiry_status(self):
        if self.is_expired:
            return "expired"
        if self.is_near_expiry:
            return "near_expiry"
        return "fresh"

    @property
    def expiry_date(self):
        """Perishability cut-off: harvest date + EXPIRY_MONTHS."""
        from config import Config
        return self.harvest_date + relativedelta(months=Config.EXPIRY_MONTHS)

    def to_dict(self):
        gallery = []
        if self.image_path:
            gallery.append(self.image_path)
        for bi in self.images:
            if bi.image_path and bi.image_path not in gallery:
                gallery.append(bi.image_path)
        return {
            "id": self.id,
            "warehouse_id": self.warehouse_id,
            "warehouse_name": self.warehouse.name if self.warehouse else None,
            "warehouse_location": self.warehouse.location if self.warehouse else None,
            "batch_id": self.batch_id,        # spec: batch_code
            "grade": self.grade,
            "qty_kg": float(self.qty_kg),     # spec: quantity_kg
            "harvest_date": self.harvest_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat(),
            "price_per_kg": round(float(self.price_per_kg)),
            "certificate_path": self.certificate_path,
            "image_path": self.image_path,
            "images": [bi.to_dict() for bi in self.images],   # extra photos (id + path) for management
            "image_paths": gallery,                            # ALL unique photos for the customer gallery
            "image_count": len(gallery),
            "description": self.description,
            "is_active": self.is_active,
            "deleted": self.deleted_at is not None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "delete_ack": self.delete_ack,
            "deleted_by": self.deleted_by,
            "expiry_status": self.expiry_status,
            "near_expiry": self.is_near_expiry,
            "expired": self.is_expired,
            "orderable": (not self.is_expired) and self.is_active and float(self.qty_kg) > 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,  # added/assigned date
        }


class BatchImage(db.Model):
    __tablename__ = "batch_images"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("jaggery_batches.id", ondelete="CASCADE"), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    def to_dict(self):
        return {"id": self.id, "image_path": self.image_path}


class Promotion(db.Model):
    __tablename__ = "promotions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=False)
    min_qty = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_currently_valid(self, qty, on_date=None):
        on_date = on_date or date.today()
        return (
            self.is_active
            and self.start_date <= on_date <= self.end_date
            and float(qty) >= float(self.min_qty)
        )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "discount_percent": float(self.discount_percent),
            "min_qty": float(self.min_qty),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "is_active": self.is_active,
        }


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assigned_warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id", ondelete="SET NULL")
    )
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    customer_seq = db.Column(db.Integer)  # this customer's Nth order (permanent, never reused)
    delivery_address = db.Column(db.Text, nullable=False)
    pincode = db.Column(db.String(60))   # delivery location: MM city (local) or country (foreign)
    delivery_scope = db.Column(db.String(10), nullable=False, default="local")  # local | foreign
    preferred_date = db.Column(db.Date)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=0)       # spec: total_amount
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)  # spec: discount_applied
    delivery_charge = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)    # spec: final_amount
    fulfillment = db.Column(db.String(10), nullable=False, default="delivery")  # delivery | pickup
    payment_method = db.Column(db.String(20))      # cod | kpay | wavepay | ayapay | cbpay | yomapay | bank
    payment_status = db.Column(db.String(20), nullable=False, default="unpaid")  # unpaid | paid
    payment_reference = db.Column(db.String(120))
    payment_phone = db.Column(db.String(30))       # phone entered on the payment form
    # --- consolidated multi-warehouse checkout (see backend/consolidated/) ---
    client_token = db.Column(db.String(64))        # retry-safe checkout (unique index)
    refunded_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    # none → held (in platform escrow) → released | refunded
    escrow_status = db.Column(db.String(20), nullable=False, default="none")
    promotion_id = db.Column(db.Integer, db.ForeignKey("promotions.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)             # spec: order_date
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)

    customer = db.relationship("User")
    warehouse = db.relationship("Warehouse")
    promotion = db.relationship("Promotion")
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")
    review = db.relationship("Review", uselist=False, backref="order")

    @property
    def grand_total(self):
        return round(float(self.total_price)) + round(float(self.delivery_charge))

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else None,
            "customer_phone": self.customer.phone if self.customer else None,
            "customer_seq": self.customer_seq,
            "assigned_warehouse_id": self.assigned_warehouse_id,
            "warehouse_name": self.warehouse.name if self.warehouse else None,
            "status": self.status,
            "delivery_address": self.delivery_address,
            "pincode": self.pincode,
            "delivery_scope": self.delivery_scope,
            "preferred_date": self.preferred_date.isoformat() if self.preferred_date else None,
            "subtotal": round(float(self.subtotal)),
            "discount_amount": round(float(self.discount_amount)),
            "delivery_charge": round(float(self.delivery_charge)),
            "total_price": round(float(self.total_price)),
            "grand_total": self.grand_total,
            "fulfillment": self.fulfillment,
            "payment_method": self.payment_method,
            "payment_method_label": {
                "cod": "Pay on delivery", "kpay": "KPay", "wavepay": "Wave Pay",
                "ayapay": "AYA Pay", "cbpay": "CB Pay", "yomapay": "Yoma Pay",
                "bank": "Bank Transfer",
            }.get(self.payment_method, self.payment_method),
            "payment_status": self.payment_status,
            "payment_reference": self.payment_reference,
            "payment_phone": self.payment_phone,
            "promotion_id": self.promotion_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "has_review": self.review is not None,
            "items": [i.to_dict() for i in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    # Which warehouse's slice this line belongs to. NULL on legacy single-warehouse
    # orders. Invariant: sub_orders.order_id == order_items.order_id.
    sub_order_id = db.Column(db.Integer, db.ForeignKey("sub_orders.id", ondelete="CASCADE"),
                             index=True)
    batch_pk = db.Column(
        db.Integer, db.ForeignKey("jaggery_batches.id", ondelete="RESTRICT"), nullable=False
    )
    qty_kg = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    line_total = db.Column(db.Numeric(12, 2), nullable=False)

    batch = db.relationship("JaggeryBatch")

    def to_dict(self):
        return {
            "id": self.id,
            "batch_pk": self.batch_pk,          # spec: batch_id
            "batch_id": self.batch.batch_id if self.batch else None,
            "grade": self.batch.grade if self.batch else None,
            "warehouse_name": (self.batch.warehouse.name
                               if self.batch and self.batch.warehouse else None),  # product owner
            "warehouse_phone": (self.batch.warehouse.phone
                                if self.batch and self.batch.warehouse else None),
            "qty_kg": float(self.qty_kg),        # spec: quantity_kg
            "unit_price": round(float(self.unit_price)),  # spec: price_per_kg
            "line_total": round(float(self.line_total)),
        }


# ---------------------------------------------------------------- v2 models
class Wishlist(db.Model):
    __tablename__ = "wishlist"
    __table_args__ = (db.UniqueConstraint("customer_id", "batch_id"),)

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("jaggery_batches.id", ondelete="CASCADE"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    batch = db.relationship("JaggeryBatch")

    def to_dict(self):
        d = {"id": self.id, "batch_id": self.batch_id, "added_at": self.added_at.isoformat()}
        if self.batch:
            d["batch"] = self.batch.to_dict()
        return d


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    rating = db.Column(db.SmallInteger, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else None,
            "warehouse_id": self.warehouse_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PriceAlert(db.Model):
    __tablename__ = "price_alerts"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("jaggery_batches.id", ondelete="CASCADE"), nullable=False)
    desired_price = db.Column(db.Numeric(10, 2), nullable=False)
    is_notified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    batch = db.relationship("JaggeryBatch")

    def to_dict(self):
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "batch_code": self.batch.batch_id if self.batch else None,
            "desired_price": float(self.desired_price),
            "current_price": float(self.batch.price_per_kg) if self.batch else None,
            "is_notified": self.is_notified,
        }


class StockTransfer(db.Model):
    __tablename__ = "stock_transfers"

    id = db.Column(db.Integer, primary_key=True)
    from_warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    to_warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("jaggery_batches.id", ondelete="CASCADE"), nullable=False)
    quantity_kg = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))

    from_wh = db.relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_wh = db.relationship("Warehouse", foreign_keys=[to_warehouse_id])
    batch = db.relationship("JaggeryBatch")

    def to_dict(self):
        return {
            "id": self.id,
            "from_warehouse_id": self.from_warehouse_id,
            "from_warehouse": self.from_wh.name if self.from_wh else None,
            "to_warehouse_id": self.to_warehouse_id,
            "to_warehouse": self.to_wh.name if self.to_wh else None,
            "batch_id": self.batch_id,
            "batch_code": self.batch.batch_id if self.batch else None,
            "quantity_kg": float(self.quantity_kg),
            "status": self.status,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
        }


class DeliveryCharge(db.Model):
    __tablename__ = "delivery_charges"

    id = db.Column(db.Integer, primary_key=True)
    pincode = db.Column(db.String(60), nullable=False, unique=True)  # location name (city or country)
    charge_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "pincode": self.pincode, "charge_amount": round(float(self.charge_amount)),
                "created_at": self.created_at.isoformat() if self.created_at else None}


class AbandonedCart(db.Model):
    __tablename__ = "abandoned_carts"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    items_json = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else None,
            "customer_email": self.customer.email if self.customer else None,
            "items": self.items_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class Advertisement(db.Model):
    """Daily advertisement shown on the customer side (admin-managed)."""
    __tablename__ = "advertisements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text)
    icon = db.Column(db.String(16), nullable=False, default="📣")
    accent = db.Column(db.String(20), nullable=False, default="amber")
    link_url = db.Column(db.String(500))
    link_label = db.Column(db.String(80))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    starts_on = db.Column(db.Date)
    ends_on = db.Column(db.Date)
    created_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_live(self, today=None):
        """True if the ad is active and within its scheduled date window today."""
        if not self.is_active:
            return False
        today = today or date.today()
        if self.starts_on and self.starts_on > today:
            return False
        if self.ends_on and self.ends_on < today:
            return False
        return True

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "icon": self.icon or "📣",
            "accent": self.accent or "amber",
            "link_url": self.link_url,
            "link_label": self.link_label,
            "is_active": self.is_active,
            "starts_on": self.starts_on.isoformat() if self.starts_on else None,
            "ends_on": self.ends_on.isoformat() if self.ends_on else None,
            "is_live": self.is_live(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SubscriptionPlan(db.Model):
    __tablename__ = "subscription_plans"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    duration_months = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "duration_months": self.duration_months,
            "price": round(float(self.price)),
            "is_active": self.is_active,
        }


class WarehouseSubscription(db.Model):
    __tablename__ = "warehouse_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("subscription_plans.id", ondelete="SET NULL"))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    price_paid = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    plan = db.relationship("SubscriptionPlan")
    warehouse = db.relationship("Warehouse")

    @property
    def is_active(self):
        return self.status == "active" and self.end_date >= date.today()

    @property
    def days_remaining(self):
        return max(0, (self.end_date - date.today()).days)

    def to_dict(self):
        return {
            "id": self.id,
            "warehouse_id": self.warehouse_id,
            "warehouse_name": self.warehouse.name if self.warehouse else None,
            "plan_id": self.plan_id,
            "plan_name": self.plan.name if self.plan else None,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "price_paid": round(float(self.price_paid)),
            "status": self.status,
            "active": self.is_active,
            "days_remaining": self.days_remaining,
        }


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey("warehouse_subscriptions.id", ondelete="SET NULL"))
    plan_id = db.Column(db.Integer, db.ForeignKey("subscription_plans.id", ondelete="SET NULL"))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    payer = db.Column(db.String(120))
    reference = db.Column(db.String(120))
    status = db.Column(db.String(20), nullable=False, default="paid")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    warehouse = db.relationship("Warehouse")
    plan = db.relationship("SubscriptionPlan")
    subscription = db.relationship("WarehouseSubscription")

    def to_dict(self):
        labels = {"kpay": "KPay", "wavepay": "Wave Pay", "ayapay": "AYA Pay",
                  "cbpay": "CB Pay", "yomapay": "Yoma Pay", "bank": "Bank Transfer"}
        return {
            "id": self.id,
            "warehouse_id": self.warehouse_id,
            "warehouse_name": self.warehouse.name if self.warehouse else None,
            "plan_name": self.plan.name if self.plan else None,
            "amount": round(float(self.amount)),
            "method": self.method,
            "method_label": labels.get(self.method, self.method),
            "payer": self.payer,
            "reference": self.reference,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # the subscription period this payment bought (for the combined
            # purchase & payment history view)
            "subscription_id": self.subscription_id,
            "start_date": self.subscription.start_date.isoformat() if self.subscription else None,
            "end_date": self.subscription.end_date.isoformat() if self.subscription else None,
            "sub_active": self.subscription.is_active if self.subscription else None,
        }


class ProductRequest(db.Model):
    __tablename__ = "product_requests"

    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    batch_code = db.Column(db.String(60), nullable=False)  # used as the Product name
    grade = db.Column(db.String(1), nullable=False)
    qty_kg = db.Column(db.Numeric(10, 2), nullable=False)
    harvest_date = db.Column(db.Date, nullable=False)
    price_per_kg = db.Column(db.Numeric(10, 2), nullable=False)
    image_path = db.Column(db.String(255))
    extra_images = db.Column(db.Text)  # comma-separated extra photo filenames (copied to batch on approval)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="pending")
    admin_note = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_batch_id = db.Column(db.Integer, db.ForeignKey("jaggery_batches.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

    warehouse = db.relationship("Warehouse")
    requester = db.relationship("User", foreign_keys=[requested_by])

    def to_dict(self):
        return {
            "id": self.id,
            "warehouse_id": self.warehouse_id,
            "warehouse_name": self.warehouse.name if self.warehouse else None,
            "requested_by_name": self.requester.name if self.requester else None,
            "batch_code": self.batch_code,
            "product_name": self.batch_code,
            "grade": self.grade,
            "qty_kg": float(self.qty_kg),
            "harvest_date": self.harvest_date.isoformat(),
            "price_per_kg": round(float(self.price_per_kg)),
            "image_path": self.image_path,
            "description": self.description,
            "status": self.status,
            "admin_note": self.admin_note,
            "created_batch_id": self.created_batch_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


class OrderMessage(db.Model):
    __tablename__ = "order_messages"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    sender_role = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender.name if self.sender else "—",
            "sender_role": self.sender_role,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SiteContent(db.Model):
    """Admin-editable page copy (the About Us page), one JSON blob per page key.
    Only the overridden fields are stored — anything absent falls back to the
    built-in bilingual text in the template."""
    __tablename__ = "site_content"

    key = db.Column(db.String(40), primary_key=True)
    data = db.Column(db.JSON, nullable=False, default=dict)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "key": self.key,
            "data": self.data or {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else None,
            "user_email": self.user.email if self.user else None,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
