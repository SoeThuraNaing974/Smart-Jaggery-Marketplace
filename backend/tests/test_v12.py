"""KPay-style 6-digit payment PIN: create once, then verify at checkout."""


def test_pin_initially_unset(staff_client):
    assert staff_client.get("/api/warehouse/payment-pin").get_json()["pin_set"] is False
    v = staff_client.post("/api/warehouse/verify-pin", json={"pin": "123456"}).get_json()
    assert v == {"ok": False, "pin_set": False}


def test_pin_must_be_exactly_6_digits(staff_client):
    for bad in ["1234", "1234567", "12ab56", ""]:
        assert staff_client.post("/api/warehouse/payment-pin",
                                 json={"new_pin": bad}).status_code == 400


def test_create_then_verify_pin(staff_client):
    # KPay-style: set the 6-digit PIN (no account password needed)
    assert staff_client.post("/api/warehouse/payment-pin",
                             json={"new_pin": "246810"}).status_code == 200
    assert staff_client.get("/api/warehouse/payment-pin").get_json()["pin_set"] is True
    assert staff_client.post("/api/warehouse/verify-pin", json={"pin": "246810"}).get_json()["ok"] is True
    assert staff_client.post("/api/warehouse/verify-pin", json={"pin": "000000"}).get_json()["ok"] is False


def test_customer_cannot_use_pin_endpoints(customer_client):
    assert customer_client.get("/api/warehouse/payment-pin").status_code == 403
    assert customer_client.post("/api/warehouse/verify-pin", json={"pin": "1"}).status_code == 403
    assert customer_client.post("/api/warehouse/payment-pin", json={"new_pin": "123456"}).status_code == 403
