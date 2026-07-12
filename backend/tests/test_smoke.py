"""End-to-end smoke tests covering auth, business rules, and the order lifecycle."""


def _batches(client):
    return {b["batch_id"]: b for b in client.get("/api/batches").get_json()}


# --- auth ------------------------------------------------------------------
def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_register_and_login(client):
    r = client.post("/api/register", json={
        "name": "New", "email": "new@t.local", "password": "secret1"})
    assert r.status_code == 201
    assert r.get_json()["user"]["role"] == "customer"

    r = client.post("/api/login", json={"email": "new@t.local", "password": "secret1"})
    assert r.status_code == 200
    assert "token" in r.get_json()


def test_login_wrong_password(client):
    r = client.post("/api/login", json={"email": "cust@t.local", "password": "nope"})
    assert r.status_code == 401


def test_protected_route_requires_auth(client):
    assert client.get("/api/orders").status_code == 401


def test_role_enforced(customer_client):
    # a customer may not hit admin endpoints
    assert customer_client.get("/api/admin/orders").status_code == 403


# --- business rules --------------------------------------------------------
def test_expired_batch_not_orderable(customer_client):
    old = _batches(customer_client)["B-OLD"]  # harvested ~320 days ago => expired
    assert old["expired"] is True
    assert old["orderable"] is False

    r = customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": old["id"], "qty_kg": 2}]})
    assert r.status_code == 422
    assert "EXPIRED" in r.get_json()["error"]


def test_insufficient_stock_rejected(customer_client):
    fresh = _batches(customer_client)["B-FRESH"]
    r = customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": fresh["id"], "qty_kg": 9999}]})
    assert r.status_code == 422
    assert "insufficient stock" in r.get_json()["error"]


def test_promotion_auto_applies_and_stock_decrements(customer_client):
    fresh = _batches(customer_client)["B-FRESH"]
    before = fresh["qty_kg"]

    r = customer_client.post("/api/orders", json={
        "delivery_address": "12 MG Road",
        "items": [{"batch_pk": fresh["id"], "qty_kg": 6}]})
    assert r.status_code == 201
    body = r.get_json()

    # 6kg * 50 = 300, 10% promo => 30 discount => 270 total
    assert body["order"]["subtotal"] == 300.0
    assert body["order"]["discount_amount"] == 30.0
    assert body["order"]["total_price"] == 270.0
    assert body["applied_promotion"]["title"] == "10% off 5kg+"

    after = _batches(customer_client)["B-FRESH"]["qty_kg"]
    assert after == before - 6


def test_no_promo_below_min_qty(customer_client):
    fresh = _batches(customer_client)["B-FRESH"]
    r = customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": fresh["id"], "qty_kg": 2}]})
    assert r.status_code == 201
    assert r.get_json()["applied_promotion"] is None
    assert r.get_json()["order"]["discount_amount"] == 0.0


def test_cancel_only_when_pending(customer_client):
    fresh = _batches(customer_client)["B-FRESH"]
    oid = customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": fresh["id"], "qty_kg": 3}]
    }).get_json()["order"]["id"]

    # cancel restores stock
    before = _batches(customer_client)["B-FRESH"]["qty_kg"]
    r = customer_client.post(f"/api/orders/{oid}/cancel")
    assert r.status_code == 200
    after = _batches(customer_client)["B-FRESH"]["qty_kg"]
    assert after == before + 3

    # second cancel now fails (status is 'cancelled')
    assert customer_client.post(f"/api/orders/{oid}/cancel").status_code == 422


# --- full lifecycle --------------------------------------------------------
def test_order_lifecycle(customer_client, admin_client, staff_client):
    fresh = _batches(customer_client)["B-FRESH"]
    oid = customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": fresh["id"], "qty_kg": 5}]
    }).get_json()["order"]["id"]

    # admin assigns to warehouse 1
    r = admin_client.post(f"/api/admin/orders/{oid}/assign", json={"warehouse_id": 1})
    assert r.status_code == 200 and r.get_json()["order"]["status"] == "assigned"

    # staff: assigned -> packed -> shipped
    assert staff_client.post(f"/api/warehouse/orders/{oid}/status",
                             json={"status": "packed"}).status_code == 200
    assert staff_client.post(f"/api/warehouse/orders/{oid}/status",
                             json={"status": "shipped"}).status_code == 200
    # illegal jump rejected
    assert staff_client.post(f"/api/warehouse/orders/{oid}/status",
                             json={"status": "delivered"}).status_code == 422

    # admin: shipped -> delivered
    r = admin_client.post(f"/api/admin/orders/{oid}/deliver")
    assert r.status_code == 200 and r.get_json()["order"]["status"] == "delivered"


def test_admin_csv_export(admin_client, customer_client):
    fresh = _batches(customer_client)["B-FRESH"]
    customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": fresh["id"], "qty_kg": 5}]})

    r = admin_client.get("/api/admin/reports/export?period=monthly")
    assert r.status_code == 200
    assert r.mimetype == "text/csv"
    # report now includes details (title, totals) + a numbered daily table
    assert b"Sales Report" in r.data
    assert b"Total revenue ($)" in r.data
    assert b"No.,Date,Qty (kg),Revenue ($)" in r.data
