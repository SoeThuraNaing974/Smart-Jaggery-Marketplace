"""v15 — guests may browse the shop, but buying requires a login."""


# ---- open to everyone (no token at all) ----------------------------------
def test_guest_can_browse_the_catalogue(client):
    r = client.get("/api/batches")
    assert r.status_code == 200
    batch_ids = [b["batch_id"] for b in r.get_json()]
    assert "B-FRESH" in batch_ids


def test_guest_sees_only_live_products(client, app):
    """A guest gets the same filtered view as a customer: nothing deactivated."""
    from db import db
    from models import JaggeryBatch
    with app.app_context():
        fresh = JaggeryBatch.query.filter_by(batch_id="B-FRESH").first()
        fresh.is_active = False
        db.session.commit()
    ids = [b["batch_id"] for b in client.get("/api/batches").get_json()]
    assert "B-FRESH" not in ids


def test_guest_can_read_promotions_ads_announcements_ratings(client):
    for path in ("/api/promotions/active", "/api/announcements/active",
                 "/api/advertisements/active", "/api/warehouses/ratings"):
        assert client.get(path).status_code == 200, path


def test_a_stale_or_bogus_token_still_browses_as_a_guest(client):
    """An expired cookie must not lock someone out of the shop front."""
    r = client.get("/api/batches", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 200


# ---- still closed to guests ---------------------------------------------
def test_guest_cannot_order_or_see_private_data(client):
    assert client.get("/api/orders").status_code == 401
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/orders", json={"delivery_address": "x", "items": []}).status_code == 401
    assert client.post("/api/checkout", json={}).status_code == 401
    assert client.get("/api/delivery-quote?pincode=Yangon").status_code == 401
    assert client.get("/api/wishlist").status_code == 401


def test_admin_only_views_stay_admin_only_for_guests(client):
    assert client.get("/api/admin/batches").status_code == 401
    assert client.get("/api/admin/escrow").status_code == 401


# ---- logged-in behaviour unchanged --------------------------------------
def test_customer_still_sees_the_catalogue(customer_client):
    assert customer_client.get("/api/batches").status_code == 200


def test_warehouse_sees_inactive_stock_a_guest_cannot(staff_client, client, app):
    """The role-based visibility rule survived the switch to optional auth."""
    from db import db
    from models import JaggeryBatch
    with app.app_context():
        b = JaggeryBatch.query.filter_by(batch_id="B-FRESH").first()
        b.is_active = False
        db.session.commit()
    staff_ids = [x["batch_id"] for x in staff_client.get("/api/batches").get_json()]
    guest_ids = [x["batch_id"] for x in client.get("/api/batches").get_json()]
    assert "B-FRESH" in staff_ids and "B-FRESH" not in guest_ids
