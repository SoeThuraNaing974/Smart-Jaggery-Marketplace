"""v14 — checkout delivery location (Local city / Foreign country) pricing."""


def _fresh_id(client):
    return {b["batch_id"]: b for b in client.get("/api/batches").get_json()}["B-FRESH"]["id"]


def test_delivery_locations_lists_admin_charges(customer_client, admin_client):
    admin_client.post("/api/admin/delivery-charges", json={"pincode": "Yangon", "charge_amount": 3000})
    body = customer_client.get("/api/delivery-locations").get_json()
    assert {"location": "Yangon", "charge": 3000} in body["locations"]
    assert body["default_charge"] >= 0


def test_local_city_charge_is_the_admin_amount(customer_client, admin_client):
    admin_client.post("/api/admin/delivery-charges", json={"pincode": "Mandalay", "charge_amount": 2500})
    r = customer_client.post("/api/orders", json={
        "delivery_address": "No. 5, Ward 3", "pincode": "Mandalay", "delivery_scope": "local",
        "items": [{"batch_pk": _fresh_id(customer_client), "qty_kg": 4}]})
    assert r.get_json()["order"]["delivery_charge"] == 2500.0


def test_city_lookup_ignores_case_and_spacing(customer_client, admin_client):
    admin_client.post("/api/admin/delivery-charges", json={"pincode": "Taunggyi", "charge_amount": 1800})
    q = customer_client.get("/api/delivery-quote?pincode=%20taunggyi%20&scope=local").get_json()
    assert q["charge"] == 1800.0


def test_foreign_country_falls_back_to_the_foreign_row(customer_client, admin_client):
    admin_client.post("/api/admin/delivery-charges", json={"pincode": "Foreign", "charge_amount": 21000})
    admin_client.post("/api/admin/delivery-charges", json={"pincode": "Thailand", "charge_amount": 23000})
    # priced country uses its own (in-band) amount
    assert customer_client.get(
        "/api/delivery-quote?pincode=Thailand&scope=foreign").get_json()["charge"] == 23000.0
    # a country the admin didn't price uses its built-in per-country fee
    assert customer_client.get(
        "/api/delivery-quote?pincode=Japan&scope=foreign").get_json()["charge"] == 38000.0
    # a country outside the built-in list falls back to the catch-all "Foreign" row
    assert customer_client.get(
        "/api/delivery-quote?pincode=Greenland&scope=foreign").get_json()["charge"] == 21000.0
    r = customer_client.post("/api/orders", json={
        "delivery_address": "12 Nuuk Street", "pincode": "Greenland", "delivery_scope": "foreign",
        "items": [{"batch_pk": _fresh_id(customer_client), "qty_kg": 3}]})
    assert r.get_json()["order"]["delivery_charge"] == 21000.0


def test_pickup_is_still_free_whatever_the_location(customer_client, admin_client):
    admin_client.post("/api/admin/delivery-charges", json={"pincode": "Yangon", "charge_amount": 3000})
    r = customer_client.post("/api/orders", json={
        "delivery_address": "x", "pincode": "Yangon", "delivery_scope": "local",
        "fulfillment": "pickup",
        "items": [{"batch_pk": _fresh_id(customer_client), "qty_kg": 2}]})
    assert r.get_json()["order"]["delivery_charge"] == 0.0


def test_long_foreign_location_is_stored(customer_client, admin_client):
    """pincode used to be VARCHAR(12) — country names are longer than that."""
    admin_client.post("/api/admin/delivery-charges",
                      json={"pincode": "United Arab Emirates", "charge_amount": 26000})
    r = customer_client.post("/api/orders", json={
        "delivery_address": "x", "pincode": "United Arab Emirates", "delivery_scope": "foreign",
        "items": [{"batch_pk": _fresh_id(customer_client), "qty_kg": 2}]})
    o = r.get_json()["order"]
    assert o["pincode"] == "United Arab Emirates"
    assert o["delivery_charge"] == 26000.0
