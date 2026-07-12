"""Warehouse product-upload requests, gated by subscription, approved by admin."""
from datetime import date

from db import db
from models import SubscriptionPlan, WarehouseSubscription
from dateutil.relativedelta import relativedelta


def _activate_sub(app, wid=1):
    with app.app_context():
        plan = SubscriptionPlan(name="1 Month", duration_months=1, price=499)
        db.session.add(plan)
        db.session.flush()
        db.session.add(WarehouseSubscription(
            warehouse_id=wid, plan_id=plan.id, start_date=date.today(),
            end_date=date.today() + relativedelta(months=1), price_paid=499, status="active"))
        db.session.commit()


def _req_body(code="REQ-1"):
    # submitted as multipart/form fields (product_name = the product/batch name)
    return {"product_name": code, "grade": "A", "qty_kg": 60,
            "harvest_date": "2026-05-20", "price_per_kg": 58,
            "description": "Pure sugarcane jaggery; boosts energy & aids digestion"}


def test_request_blocked_without_subscription(staff_client):
    r = staff_client.post("/api/warehouse/product-requests", data=_req_body())
    assert r.status_code == 403
    assert "subscription" in r.get_json()["error"]


def test_request_then_admin_approves_creates_batch(app, staff_client, admin_client, customer_client):
    _activate_sub(app)
    r = staff_client.post("/api/warehouse/product-requests", data=_req_body("REQ-A"))
    assert r.status_code == 201
    rid = r.get_json()["request"]["id"]

    # admin sees it pending
    pend = admin_client.get("/api/admin/product-requests?status=pending").get_json()
    assert any(x["id"] == rid for x in pend)

    # approve -> a real batch appears in the catalogue
    d = admin_client.post(f"/api/admin/product-requests/{rid}/decision", json={"decision": "approved"})
    assert d.status_code == 200
    assert d.get_json()["request"]["status"] == "approved"
    batches = customer_client.get("/api/batches").get_json()
    made = next(b for b in batches if b["batch_id"] == "REQ-A")
    # the ingredients/effectiveness description carries onto the published batch
    assert "boosts energy" in (made["description"] or "")


def test_admin_reject(app, staff_client, admin_client, customer_client):
    _activate_sub(app)
    rid = staff_client.post("/api/warehouse/product-requests",
                            data=_req_body("REQ-R")).get_json()["request"]["id"]
    d = admin_client.post(f"/api/admin/product-requests/{rid}/decision",
                          json={"decision": "rejected", "note": "low grade"})
    assert d.status_code == 200 and d.get_json()["request"]["status"] == "rejected"
    # not published
    assert "REQ-R" not in [b["batch_id"] for b in customer_client.get("/api/batches").get_json()]


def test_cannot_decide_twice(app, staff_client, admin_client):
    _activate_sub(app)
    rid = staff_client.post("/api/warehouse/product-requests",
                            data=_req_body("REQ-2")).get_json()["request"]["id"]
    admin_client.post(f"/api/admin/product-requests/{rid}/decision", json={"decision": "approved"})
    again = admin_client.post(f"/api/admin/product-requests/{rid}/decision", json={"decision": "rejected"})
    assert again.status_code == 422


def test_long_description_capped(app, staff_client):
    _activate_sub(app)
    body = _req_body("REQ-LONG")
    body["description"] = "x" * 2000  # way over the limit
    r = staff_client.post("/api/warehouse/product-requests", data=body)
    assert r.status_code == 201
    assert len(r.get_json()["request"]["description"]) == 1000  # capped


def test_customer_cannot_access(customer_client):
    assert customer_client.post("/api/warehouse/product-requests", data=_req_body()).status_code == 403
    assert customer_client.get("/api/admin/product-requests").status_code == 403

