"""Admin batch CRUD across all warehouses."""


def test_admin_batch_crud(admin_client, customer_client):
    # CREATE
    r = admin_client.post("/api/admin/batches", json={
        "warehouse_id": 1, "batch_id": "ADM-001", "grade": "A",
        "qty_kg": 80, "harvest_date": "2026-05-01", "price_per_kg": 55})
    assert r.status_code == 201
    pk = r.get_json()["batch"]["id"]

    # READ (admin list includes it)
    listing = admin_client.get("/api/admin/batches").get_json()
    assert any(b["batch_id"] == "ADM-001" for b in listing)

    # UPDATE
    u = admin_client.put(f"/api/admin/batches/{pk}", json={"qty_kg": 120, "price_per_kg": 50})
    assert u.status_code == 200 and u.get_json()["batch"]["qty_kg"] == 120.0

    # DELETE (no orders reference it -> allowed)
    assert admin_client.delete(f"/api/admin/batches/{pk}").status_code == 200
    assert not any(b["batch_id"] == "ADM-001"
                   for b in admin_client.get("/api/admin/batches").get_json())


def test_admin_create_validation(admin_client):
    assert admin_client.post("/api/admin/batches", json={"batch_id": "X"}).status_code == 400
    assert admin_client.post("/api/admin/batches", json={
        "warehouse_id": 999, "batch_id": "Y", "grade": "A",
        "qty_kg": 1, "harvest_date": "2026-01-01", "price_per_kg": 1}).status_code == 400


def test_admin_cannot_delete_referenced_batch(admin_client, customer_client):
    bid = next(b["id"] for b in customer_client.get("/api/batches").get_json()
               if b["batch_id"] == "B-FRESH")
    customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": bid, "qty_kg": 2}]})
    r = admin_client.delete(f"/api/admin/batches/{bid}")
    assert r.status_code == 409
    assert "is_active=false" in r.get_json()["error"]


def test_admin_price_drop_fires_alerts(admin_client, customer_client):
    bid = next(b["id"] for b in customer_client.get("/api/batches").get_json()
               if b["batch_id"] == "B-FRESH")  # price 50
    customer_client.post("/api/price-alerts", json={"batch_id": bid, "desired_price": 45})
    r = admin_client.put(f"/api/admin/batches/{bid}", json={"price_per_kg": 40})
    assert r.get_json()["price_alerts_fired"] == 1


def test_customer_cannot_manage_batches(customer_client):
    assert customer_client.get("/api/admin/batches").status_code == 403
    assert customer_client.post("/api/admin/batches", json={}).status_code == 403
