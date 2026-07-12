"""Pytest fixtures: in-memory SQLite app + seeded demo data + per-role clients."""
import os
import sys
from datetime import date, timedelta

import pytest
from sqlalchemy.pool import StaticPool

# make backend/ importable when running `pytest` from the backend dir
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from db import db  # noqa: E402
from models import User, Warehouse, JaggeryBatch, Promotion  # noqa: E402
from auth import hash_password  # noqa: E402

# A single shared in-memory connection so tables survive across requests.
TEST_CONFIG = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite://",
    "SQLALCHEMY_ENGINE_OPTIONS": {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    },
}


@pytest.fixture
def app():
    app = create_app(TEST_CONFIG)
    with app.app_context():
        db.create_all()
        _seed()
        yield app
        db.session.remove()
        db.drop_all()


def _seed():
    admin = User(name="Admin", email="admin@t.local",
                 password_hash=hash_password("admin123"), role="admin")
    wh = Warehouse(name="WH1", location="Pune")
    db.session.add_all([admin, wh])
    db.session.flush()

    staff = User(name="Staff", email="staff@t.local",
                 password_hash=hash_password("staff123"),
                 role="warehouse", warehouse_id=wh.id)
    customer = User(name="Cust", email="cust@t.local",
                    password_hash=hash_password("cust123"), role="customer")

    fresh = JaggeryBatch(warehouse_id=wh.id, batch_id="B-FRESH", grade="A",
                         qty_kg=100, harvest_date=date.today() - timedelta(days=10),
                         price_per_kg=50)
    expired = JaggeryBatch(warehouse_id=wh.id, batch_id="B-OLD", grade="C",
                           qty_kg=100, harvest_date=date.today() - timedelta(days=320),
                           price_per_kg=30)
    promo = Promotion(title="10% off 5kg+", discount_percent=10, min_qty=5,
                      start_date=date.today() - timedelta(days=1),
                      end_date=date.today() + timedelta(days=10), is_active=True)
    db.session.add_all([staff, customer, fresh, expired, promo])
    db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


def _logged_in_client(app, email, password):
    """Each role gets its OWN test client (and thus its own cookie jar), so a
    test can drive several roles at once without their tokens clobbering."""
    c = app.test_client()
    r = c.post("/api/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.get_json()
    return c


@pytest.fixture
def customer_client(app):
    return _logged_in_client(app, "cust@t.local", "cust123")


@pytest.fixture
def staff_client(app):
    return _logged_in_client(app, "staff@t.local", "staff123")


@pytest.fixture
def admin_client(app):
    return _logged_in_client(app, "admin@t.local", "admin123")
