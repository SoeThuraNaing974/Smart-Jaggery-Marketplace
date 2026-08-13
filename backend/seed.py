"""Seed demo data: admin, a warehouse + staff, batches, a promotion, a customer.

Run:  python seed.py
Or set the env var SEED_DEMO=true and the app seeds itself on first boot —
that is how a fresh hosted database (e.g. on Render) gets its demo accounts.
"""
from datetime import date, timedelta

from db import db
from models import User, Warehouse, JaggeryBatch, Promotion
from auth import hash_password


def seed_demo():
    """Insert the demo data once. Needs an app context; safe to call on every
    boot — it does nothing when an admin account already exists."""
    if User.query.filter_by(role="admin").first():
        print("Seed data already present — skipping.")
        return

    admin = User(name="Site Admin", email="admin@jaggery.local",
                 password_hash=hash_password("admin123"), role="admin")

    wh = Warehouse(name="Kolhapur Central", location="Kolhapur, MH", phone="020-111-2222")
    db.session.add_all([admin, wh])
    db.session.flush()

    staff = User(name="Warehouse", email="staff@jaggery.local",
                 password_hash=hash_password("staff123"),
                 role="warehouse", warehouse_id=wh.id)

    customer = User(name="Asha Customer", email="customer@jaggery.local",
                    password_hash=hash_password("cust123"), role="customer")

    fresh = JaggeryBatch(warehouse_id=wh.id, batch_id="JAG-2026-001", grade="A",
                         qty_kg=120, harvest_date=date.today() - timedelta(days=30),
                         price_per_kg=60)
    low = JaggeryBatch(warehouse_id=wh.id, batch_id="JAG-2026-002", grade="B",
                       qty_kg=40, harvest_date=date.today() - timedelta(days=60),
                       price_per_kg=45)
    expired = JaggeryBatch(warehouse_id=wh.id, batch_id="JAG-2025-099", grade="C",
                           qty_kg=200, harvest_date=date.today() - timedelta(days=320),
                           price_per_kg=30)

    promo = Promotion(title="10% off on 5kg+", discount_percent=10, min_qty=5,
                      start_date=date.today() - timedelta(days=5),
                      end_date=date.today() + timedelta(days=30), is_active=True)

    db.session.add_all([staff, customer, fresh, low, expired, promo])
    db.session.commit()
    print("Seeded. Logins:")
    print("  admin@jaggery.local / admin123")
    print("  staff@jaggery.local / staff123")
    print("  customer@jaggery.local / cust123")


if __name__ == "__main__":
    from app import create_app

    with create_app().app_context():
        seed_demo()
