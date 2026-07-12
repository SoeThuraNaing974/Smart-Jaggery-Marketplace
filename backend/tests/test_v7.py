"""Warehouse subscription plans: admin manages plans, warehouse buys/views."""
from datetime import date
from dateutil.relativedelta import relativedelta

from db import db
from models import SubscriptionPlan


def _seed_plans(app):
    with app.app_context():
        if not SubscriptionPlan.query.first():
            db.session.add_all([
                SubscriptionPlan(name="1 Month", duration_months=1, price=499),
                SubscriptionPlan(name="1 Year", duration_months=12, price=4499),
            ])
            db.session.commit()


def test_admin_plan_crud(app, admin_client):
    r = admin_client.post("/api/admin/subscription-plans",
                          json={"name": "3 Months", "duration_months": 3, "price": 1299})
    assert r.status_code == 201
    pid = r.get_json()["plan"]["id"]
    assert admin_client.put(f"/api/admin/subscription-plans/{pid}",
                            json={"price": 1199, "is_active": False}).status_code == 200
    assert admin_client.delete(f"/api/admin/subscription-plans/{pid}").status_code == 200


def test_admin_plan_validation(admin_client):
    assert admin_client.post("/api/admin/subscription-plans",
                             json={"name": "X", "duration_months": 0, "price": 1}).status_code == 400


def test_warehouse_buys_subscription(app, staff_client):
    _seed_plans(app)
    plans = staff_client.get("/api/warehouse/subscription-plans").get_json()
    one_month = next(p for p in plans if p["duration_months"] == 1)

    # no subscription initially
    assert staff_client.get("/api/warehouse/subscription").get_json()["active"] is False

    r = staff_client.post("/api/warehouse/subscription", json={"plan_id": one_month["id"], "method": "kpay", "reference": "TXN1"})
    assert r.status_code == 201
    sub = r.get_json()["subscription"]
    assert sub["active"] is True
    assert sub["end_date"] == (date.today() + relativedelta(months=1)).isoformat()

    status = staff_client.get("/api/warehouse/subscription").get_json()
    assert status["active"] is True and status["current"]["plan_name"] == "1 Month"


def test_buying_again_extends_term(app, staff_client):
    _seed_plans(app)
    plans = staff_client.get("/api/warehouse/subscription-plans").get_json()
    one = next(p for p in plans if p["duration_months"] == 1)
    staff_client.post("/api/warehouse/subscription", json={"plan_id": one["id"], "method": "kpay", "reference": "T1"})
    r2 = staff_client.post("/api/warehouse/subscription", json={"plan_id": one["id"], "method": "wavepay", "reference": "T2"})
    # second month stacks on top of the first -> ~2 months out
    assert r2.get_json()["subscription"]["end_date"] == (date.today() + relativedelta(months=2)).isoformat()


def test_admin_sees_subscription_status(app, admin_client, staff_client):
    _seed_plans(app)
    plans = staff_client.get("/api/warehouse/subscription-plans").get_json()
    staff_client.post("/api/warehouse/subscription",
                      json={"plan_id": plans[0]["id"], "method": "kpay", "reference": "T9"})
    overview = admin_client.get("/api/admin/subscriptions").get_json()
    assert any(w["subscribed"] for w in overview)


def test_customer_cannot_buy(customer_client):
    assert customer_client.get("/api/warehouse/subscription").status_code == 403
    assert customer_client.post("/api/admin/subscription-plans", json={}).status_code == 403
