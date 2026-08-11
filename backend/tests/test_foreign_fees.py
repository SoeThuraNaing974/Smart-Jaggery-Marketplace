"""Foreign delivery fees: per-country defaults + the 20,000–50,000 Kyats band."""
from config import Config


def _quote(client, pincode, scope="foreign"):
    r = client.get(f"/api/delivery-quote?pincode={pincode}&scope={scope}")
    assert r.status_code == 200
    return r.get_json()["charge"]


def test_every_builtin_country_fee_is_inside_the_band():
    assert Config.FOREIGN_COUNTRY_FEES, "built-in country fee table must not be empty"
    for country, fee in Config.FOREIGN_COUNTRY_FEES.items():
        assert Config.FOREIGN_FEE_MIN <= fee <= Config.FOREIGN_FEE_MAX, country


def test_foreign_fee_depends_on_country(customer_client):
    assert _quote(customer_client, "Thailand") == 20000
    assert _quote(customer_client, "Japan") == 38000
    assert _quote(customer_client, "United States") == 50000
    # scope is optional when the location is a known shipping country
    assert _quote(customer_client, "Singapore", scope="") == 28000


def test_unknown_foreign_country_is_banded(customer_client):
    # no admin rows at all -> the tiny flat local default must never leak abroad
    assert _quote(customer_client, "Atlantis") == Config.FOREIGN_FEE_MIN


def test_admin_override_wins_but_stays_in_band(customer_client, admin_client):
    admin_client.post("/api/admin/delivery-charges",
                      json={"pincode": "Thailand", "charge_amount": 30000})
    assert _quote(customer_client, "Thailand") == 30000
    # out-of-band overrides are clamped when saved
    r = admin_client.post("/api/admin/delivery-charges",
                          json={"pincode": "Japan", "charge_amount": 60000})
    assert r.get_json()["delivery_charge"]["charge_amount"] == 50000
    assert _quote(customer_client, "Japan") == 50000
    r = admin_client.post("/api/admin/delivery-charges",
                          json={"pincode": "Foreign", "charge_amount": 5000})
    assert r.get_json()["delivery_charge"]["charge_amount"] == 20000
    assert _quote(customer_client, "Atlantis") == 20000


def test_order_to_foreign_country_charges_country_fee(customer_client):
    bid = next(b["id"] for b in customer_client.get("/api/batches").get_json()
               if b["batch_id"] == "B-FRESH")
    r = customer_client.post("/api/orders", json={
        "delivery_address": "x", "pincode": "Japan", "delivery_scope": "foreign",
        "items": [{"batch_pk": bid, "qty_kg": 2}]})
    assert r.status_code == 201
    assert r.get_json()["order"]["delivery_charge"] == 38000


def test_local_city_fees_unchanged(customer_client, admin_client):
    admin_client.post("/api/admin/delivery-charges",
                      json={"pincode": "Yangon", "charge_amount": 3000})
    assert _quote(customer_client, "Yangon", scope="local") == 3000
    assert _quote(customer_client, "Mandalay", scope="local") == Config.DEFAULT_DELIVERY_FEE


def test_delivery_locations_exposes_resolved_foreign_fees(customer_client, admin_client):
    admin_client.post("/api/admin/delivery-charges",
                      json={"pincode": "Thailand", "charge_amount": 25000})
    d = customer_client.get("/api/delivery-locations").get_json()
    fees = d["foreign_fees"]
    assert len(fees) == len(Config.FOREIGN_COUNTRY_FEES)
    assert all(Config.FOREIGN_FEE_MIN <= f <= Config.FOREIGN_FEE_MAX for f in fees.values())
    assert fees["thailand"] == 25000          # admin override shows through
    assert fees["japan"] == 38000             # built-in per-country fee
    assert d["foreign_default_charge"] == Config.FOREIGN_FEE_MIN  # banded flat default
