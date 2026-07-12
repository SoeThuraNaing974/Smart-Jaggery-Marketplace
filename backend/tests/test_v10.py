"""Subscription payment flow (KPay / Wave Pay / AYA Pay / CB Pay / Bank)."""
from datetime import date

from db import db
from models import SubscriptionPlan


def _plan(app):
    with app.app_context():
        if not SubscriptionPlan.query.first():
            db.session.add(SubscriptionPlan(name="1 Month", duration_months=1, price=499))
            db.session.commit()
        return SubscriptionPlan.query.first().id


def test_payment_methods_listed(app, staff_client):
    _plan(app)
    methods = staff_client.get("/api/warehouse/payment-methods").get_json()
    keys = {m["key"] for m in methods}
    assert keys == {"kpay", "wavepay", "ayapay", "cbpay", "yomapay", "bank"}
    assert all(m["account"] for m in methods)


def test_payment_required_to_subscribe(app, staff_client):
    pid = _plan(app)
    # missing method
    assert staff_client.post("/api/warehouse/subscription",
                             json={"plan_id": pid, "reference": "X"}).status_code == 400
    # bad method
    assert staff_client.post("/api/warehouse/subscription",
                             json={"plan_id": pid, "method": "paypal", "reference": "X"}).status_code == 400
    # missing reference
    assert staff_client.post("/api/warehouse/subscription",
                             json={"plan_id": pid, "method": "kpay"}).status_code == 400


def test_successful_payment_activates_and_records(app, staff_client, admin_client):
    pid = _plan(app)
    r = staff_client.post("/api/warehouse/subscription",
                          json={"plan_id": pid, "method": "ayapay",
                                "payer": "09111222333", "reference": "AYA-77"})
    assert r.status_code == 201
    body = r.get_json()
    assert body["subscription"]["active"] is True
    assert body["payment"]["method"] == "ayapay"
    assert body["payment"]["amount"] == 499.0

    # warehouse sees its payment
    mine = staff_client.get("/api/warehouse/payments").get_json()
    assert any(p["reference"] == "AYA-77" for p in mine)

    # admin sees it in the collected payments + total
    adm = admin_client.get("/api/admin/payments").get_json()
    assert adm["total_collected"] >= 499.0
    assert any(p["reference"] == "AYA-77" and p["method_label"] == "AYA Pay" for p in adm["payments"])


def test_pay_with_yoma(app, staff_client):
    pid = _plan(app)
    r = staff_client.post("/api/warehouse/subscription",
                          json={"plan_id": pid, "method": "yomapay", "reference": "YOMA-1"})
    assert r.status_code == 201
    assert r.get_json()["payment"]["method_label"] == "Yoma Pay"


def test_customer_cannot_pay(customer_client):
    assert customer_client.get("/api/warehouse/payment-methods").status_code == 403
    assert customer_client.get("/api/admin/payments").status_code == 403
