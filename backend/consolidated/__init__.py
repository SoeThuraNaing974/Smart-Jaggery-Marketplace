"""
Consolidated Pickup & Delivery with Multi-Warehouse Order Splitting.

    from consolidated import bp as consolidated_bp
    app.register_blueprint(consolidated_bp)

Importing this package registers the new models with SQLAlchemy, so
`db.create_all()` (and the tests) pick them up. On a real database run
backend/schema_v28.sql instead — it also alters the existing tables.
"""
from .models import (SubOrder, Delivery, DeliveryStop, WarehouseWallet,   # noqa: F401
                     PayoutLedger, PlatformLedger, Refund, RiderProfile)
from .routes import bp                                                   # noqa: F401
from .settings import settings                                           # noqa: F401

__all__ = ["bp", "settings", "SubOrder", "Delivery", "DeliveryStop",
           "WarehouseWallet", "PayoutLedger", "PlatformLedger", "Refund",
           "RiderProfile"]
