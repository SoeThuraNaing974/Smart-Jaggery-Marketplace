"""Smoke tests for the v2 expanded features."""


def _fresh_id(client):
    return next(b["id"] for b in client.get("/api/batches").get_json() if b["batch_id"] == "B-FRESH")


def test_wishlist_add_and_list(customer_client):
    bid = _fresh_id(customer_client)
    assert customer_client.post("/api/wishlist", json={"batch_id": bid}).status_code == 201
    items = customer_client.get("/api/wishlist").get_json()
    assert any(w["batch_id"] == bid for w in items)


def test_review_blocked_before_delivery(customer_client):
    bid = _fresh_id(customer_client)
    oid = customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": bid, "qty_kg": 3}]
    }).get_json()["order"]["id"]
    # not delivered yet -> 422
    r = customer_client.post(f"/api/orders/{oid}/review", json={"rating": 5})
    assert r.status_code == 422


def test_review_after_delivery(customer_client, admin_client, staff_client):
    bid = _fresh_id(customer_client)
    oid = customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": bid, "qty_kg": 5}]
    }).get_json()["order"]["id"]
    admin_client.post(f"/api/admin/orders/{oid}/assign", json={"warehouse_id": 1})
    staff_client.post(f"/api/warehouse/orders/{oid}/status", json={"status": "packed"})
    staff_client.post(f"/api/warehouse/orders/{oid}/status", json={"status": "shipped"})
    admin_client.post(f"/api/admin/orders/{oid}/deliver")

    r = customer_client.post(f"/api/orders/{oid}/review", json={"rating": 4, "comment": "good"})
    assert r.status_code == 201
    assert r.get_json()["review"]["rating"] == 4


def test_delivery_charge_applied(customer_client, admin_client):
    admin_client.post("/api/admin/delivery-charges", json={"pincode": "414001", "charge_amount": 50})
    bid = _fresh_id(customer_client)
    r = customer_client.post("/api/orders", json={
        "delivery_address": "x", "pincode": "414001",
        "items": [{"batch_pk": bid, "qty_kg": 6}]})
    o = r.get_json()["order"]
    assert o["delivery_charge"] == 50.0
    assert o["grand_total"] == o["total_price"] + 50.0


def test_admin_kpis_shape(admin_client):
    k = admin_client.get("/api/admin/kpis").get_json()
    for key in ("total_orders", "total_revenue", "active_users", "pending_assignments", "total_stock_kg"):
        assert key in k
