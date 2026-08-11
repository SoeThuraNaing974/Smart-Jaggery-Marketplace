"""Admin deletes a warehouse's category → it disappears for the warehouse and
customers, and the warehouse is notified (admin_deleted list on its stock)."""


def _fresh_id(client):
    return next(b["id"] for b in client.get("/api/batches").get_json()
                if b["batch_id"] == "B-FRESH")


def test_admin_delete_hides_everywhere_and_notifies_warehouse(
        admin_client, staff_client, customer_client):
    bid = _fresh_id(customer_client)
    # referenced by an order — deletion must still work (soft delete)
    customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": bid, "qty_kg": 2}]})

    r = admin_client.delete(f"/api/admin/batches/{bid}")
    assert r.status_code == 200
    assert "warehouse has been notified" in r.get_json()["message"]

    # gone from the customer catalogue
    assert all(b["id"] != bid for b in customer_client.get("/api/batches").get_json())
    # gone from the warehouse stock…
    stock = staff_client.get("/api/warehouse/stock").get_json()
    assert all(b["id"] != bid for b in stock["batches"])
    # …but listed for the warehouse's deletion notification
    dels = stock["admin_deleted"]
    assert any(d["id"] == bid and d["deleted_by"] == "admin" for d in dels)
    # the admin's own deleted-stock alarm is NOT triggered by their own action
    assert all(d["id"] != bid for d in admin_client.get("/api/admin/deleted-stocks").get_json())
    # deleting again → already gone
    assert admin_client.delete(f"/api/admin/batches/{bid}").status_code == 404


def test_warehouse_delete_still_alarms_the_admin(staff_client, admin_client):
    pk = next(b["id"] for b in staff_client.get("/api/warehouse/stock").get_json()["batches"]
              if b["batch_id"] == "B-FRESH")
    assert staff_client.delete(f"/api/warehouse/batches/{pk}").status_code == 200
    dels = admin_client.get("/api/admin/deleted-stocks").get_json()
    assert any(d["id"] == pk and d["deleted_by"] == "warehouse" for d in dels)
    # a warehouse's own deletion is not in its admin-deleted notification list
    stock = staff_client.get("/api/warehouse/stock").get_json()
    assert all(d["id"] != pk for d in stock["admin_deleted"])
