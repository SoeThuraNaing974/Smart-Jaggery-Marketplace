"""Admin & warehouse can both edit full category details
(name, grade, qty, price, production date, description)."""


def _stock_id(staff_client, name="B-FRESH"):
    return next(b["id"] for b in staff_client.get("/api/warehouse/stock").get_json()["batches"]
                if b["batch_id"] == name)


def test_warehouse_edits_full_details(staff_client):
    pk = _stock_id(staff_client)
    r = staff_client.put(f"/api/warehouse/batches/{pk}", json={
        "batch_id": "B-RENAMED", "grade": "B", "qty_kg": 55, "price_per_kg": 70,
        "harvest_date": "2026-01-05",
        "description": "Ingredients: pure cane\n\nEffectiveness: rich in iron",
    })
    assert r.status_code == 200, r.get_json()
    b = r.get_json()["batch"]
    assert b["batch_id"] == "B-RENAMED"
    assert b["grade"] == "B"
    assert b["qty_kg"] == 55.0
    assert b["price_per_kg"] == 70
    assert b["harvest_date"] == "2026-01-05"
    assert b["description"] == "Ingredients: pure cane\n\nEffectiveness: rich in iron"


def test_warehouse_cannot_blank_the_name(staff_client):
    pk = _stock_id(staff_client)
    r = staff_client.put(f"/api/warehouse/batches/{pk}", json={"batch_id": "   "})
    assert r.status_code == 400


def test_same_category_name_can_be_reused(staff_client, admin_client, customer_client):
    """Category names are not unique anywhere in the system."""
    # warehouse renames its product to a name another product already uses
    pk = _stock_id(staff_client)
    r = staff_client.put(f"/api/warehouse/batches/{pk}", json={"batch_id": "B-OLD"})
    assert r.status_code == 200
    assert r.get_json()["batch"]["batch_id"] == "B-OLD"
    # warehouse creates a brand-new product under that same name
    r = staff_client.post("/api/warehouse/batches", json={
        "batch_id": "B-OLD", "grade": "A", "qty_kg": 5,
        "harvest_date": "2026-06-01", "price_per_kg": 40})
    assert r.status_code == 201
    # admin creates yet another with the same name
    r = admin_client.post("/api/admin/batches", json={
        "warehouse_id": 1, "batch_id": "B-OLD", "grade": "B",
        "qty_kg": 7, "harvest_date": "2026-06-02", "price_per_kg": 45})
    assert r.status_code == 201
    # all of them coexist in the warehouse's stock
    names = [b["batch_id"] for b in
             staff_client.get("/api/warehouse/stock").get_json()["batches"]]
    assert names.count("B-OLD") >= 3


def test_warehouse_saving_same_name_is_fine(staff_client):
    pk = _stock_id(staff_client)
    r = staff_client.put(f"/api/warehouse/batches/{pk}",
                         json={"batch_id": "B-FRESH", "qty_kg": 60})
    assert r.status_code == 200
    assert r.get_json()["batch"]["qty_kg"] == 60.0


def test_warehouse_clearing_description(staff_client):
    pk = _stock_id(staff_client)
    staff_client.put(f"/api/warehouse/batches/{pk}", json={"description": "something"})
    r = staff_client.put(f"/api/warehouse/batches/{pk}", json={"description": ""})
    assert r.status_code == 200
    assert r.get_json()["batch"]["description"] is None


def test_admin_edits_name_and_production_date(admin_client):
    pk = next(b["id"] for b in admin_client.get("/api/batches").get_json()
              if b["batch_id"] == "B-FRESH")
    r = admin_client.put(f"/api/admin/batches/{pk}", json={
        "batch_id": "B-ADMIN-NAME", "harvest_date": "2026-02-10",
    })
    assert r.status_code == 200, r.get_json()
    b = r.get_json()["batch"]
    assert b["batch_id"] == "B-ADMIN-NAME"
    assert b["harvest_date"] == "2026-02-10"
