"""Tests for v4: profile, password change, price-drop triggering, abandoned carts, ratings."""


def _fresh(client):
    return next(b for b in client.get("/api/batches").get_json() if b["batch_id"] == "B-FRESH")


def test_update_profile(customer_client):
    r = customer_client.put("/api/me", json={"phone": "9990001111", "pincode": "416001",
                                             "address": "12 MG Road"})
    assert r.status_code == 200
    me = customer_client.get("/api/me").get_json()["user"]
    assert me["phone"] == "9990001111" and me["pincode"] == "416001"


def test_change_password(client, customer_client):
    assert customer_client.post("/api/change-password",
                                json={"current_password": "wrong", "new_password": "abcdef"}).status_code == 403
    assert customer_client.post("/api/change-password",
                                json={"current_password": "cust123", "new_password": "newpass1"}).status_code == 200
    # new password now works, old one doesn't
    assert client.post("/api/login", json={"email": "cust@t.local", "password": "newpass1"}).status_code == 200
    assert client.post("/api/login", json={"email": "cust@t.local", "password": "cust123"}).status_code == 401


def test_price_drop_triggers_alert(customer_client, staff_client):
    b = _fresh(customer_client)  # price 50
    customer_client.post("/api/price-alerts", json={"batch_id": b["id"], "desired_price": 45})
    # not yet notified
    assert customer_client.get("/api/price-alerts").get_json()[0]["is_notified"] is False
    # staff drops price below desired -> alert fires
    r = staff_client.put(f"/api/warehouse/batches/{b['id']}", json={"price_per_kg": 40})
    assert r.status_code == 200 and r.get_json()["price_alerts_fired"] == 1
    assert customer_client.get("/api/price-alerts").get_json()[0]["is_notified"] is True


def test_no_trigger_when_price_rises(customer_client, staff_client):
    b = _fresh(customer_client)
    customer_client.post("/api/price-alerts", json={"batch_id": b["id"], "desired_price": 45})
    r = staff_client.put(f"/api/warehouse/batches/{b['id']}", json={"price_per_kg": 70})
    assert r.get_json()["price_alerts_fired"] == 0
    assert customer_client.get("/api/price-alerts").get_json()[0]["is_notified"] is False


def test_abandoned_cart_capture(customer_client, admin_client):
    r = customer_client.post("/api/cart/abandon", json={"items": [{"batch_pk": 1, "qty_kg": 3}]})
    assert r.status_code == 200
    carts = admin_client.get("/api/admin/abandoned-carts").get_json()
    assert any(c["customer_email"] == "cust@t.local" for c in carts)


def test_warehouse_ratings(customer_client, admin_client, staff_client):
    b = _fresh(customer_client)
    oid = customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": b["id"], "qty_kg": 5}]
    }).get_json()["order"]["id"]
    admin_client.post(f"/api/admin/orders/{oid}/assign", json={"warehouse_id": 1})
    staff_client.post(f"/api/warehouse/orders/{oid}/status", json={"status": "packed"})
    staff_client.post(f"/api/warehouse/orders/{oid}/status", json={"status": "shipped"})
    admin_client.post(f"/api/admin/orders/{oid}/deliver")
    customer_client.post(f"/api/orders/{oid}/review", json={"rating": 4, "comment": "ok"})

    ratings = customer_client.get("/api/warehouses/ratings").get_json()
    assert ratings["1"]["avg"] == 4.0 and ratings["1"]["count"] == 1
