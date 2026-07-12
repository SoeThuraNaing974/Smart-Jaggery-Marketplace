"""Admin full promotion management (edit title/percent/dates, validation, delete)."""
from datetime import date, timedelta


def _make(admin_client, **over):
    body = {"title": "Test promo", "discount_percent": 10, "min_qty": 5,
            "start_date": str(date.today()), "end_date": str(date.today() + timedelta(days=10))}
    body.update(over)
    return admin_client.post("/api/admin/promotions", json=body)


def test_update_promotion_all_fields(admin_client):
    pid = _make(admin_client).get_json()["promotion"]["id"]
    r = admin_client.put(f"/api/admin/promotions/{pid}", json={
        "title": "Festive 20%", "discount_percent": 20, "min_qty": 3,
        "start_date": "2026-06-01", "end_date": "2026-06-30", "is_active": False})
    assert r.status_code == 200
    p = r.get_json()["promotion"]
    assert p["title"] == "Festive 20%" and p["discount_percent"] == 20.0
    assert p["min_qty"] == 3.0 and p["start_date"] == "2026-06-01"
    assert p["end_date"] == "2026-06-30" and p["is_active"] is False


def test_update_rejects_bad_percent_and_dates(admin_client):
    pid = _make(admin_client).get_json()["promotion"]["id"]
    assert admin_client.put(f"/api/admin/promotions/{pid}", json={"discount_percent": 150}).status_code == 400
    assert admin_client.put(f"/api/admin/promotions/{pid}",
                            json={"start_date": "2026-06-30", "end_date": "2026-06-01"}).status_code == 400


def test_delete_promotion(admin_client):
    pid = _make(admin_client).get_json()["promotion"]["id"]
    assert admin_client.delete(f"/api/admin/promotions/{pid}").status_code == 200
    assert not any(p["id"] == pid for p in admin_client.get("/api/admin/promotions").get_json())


def test_edited_promotion_auto_applies(admin_client, customer_client):
    # edit the seeded promo to 25% and place a qualifying order -> discount reflects edit
    pid = admin_client.get("/api/admin/promotions").get_json()[0]["id"]
    admin_client.put(f"/api/admin/promotions/{pid}", json={"discount_percent": 25, "min_qty": 5})
    bid = next(b["id"] for b in customer_client.get("/api/batches").get_json()
               if b["batch_id"] == "B-FRESH")  # $50/kg
    o = customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": bid, "qty_kg": 6}]}).get_json()["order"]
    assert o["subtotal"] == 300.0 and o["discount_amount"] == 75.0  # 25% of 300


def test_customer_cannot_manage_promotions(customer_client):
    assert customer_client.put("/api/admin/promotions/1", json={"discount_percent": 5}).status_code == 403
    assert customer_client.delete("/api/admin/promotions/1").status_code == 403
