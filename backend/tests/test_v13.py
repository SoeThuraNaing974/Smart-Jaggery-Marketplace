"""PIN reset via emailed verification code (OTP)."""


def _set_pin(staff_client, pin="111111"):
    staff_client.post("/api/warehouse/payment-pin", json={"new_pin": pin})


def test_reset_request_returns_dev_code_in_dry_run(staff_client):
    _set_pin(staff_client)
    r = staff_client.post("/api/warehouse/pin-reset/request")
    assert r.status_code == 200
    body = r.get_json()
    assert body["sent"] is True
    assert "@" in body["email"] and body["email"].startswith("s***")  # masked
    assert body.get("delivery") == "dry_run"
    assert len(body["dev_code"]) == 6  # surfaced because no SMTP configured


def test_verify_code(staff_client):
    _set_pin(staff_client)
    code = staff_client.post("/api/warehouse/pin-reset/request").get_json()["dev_code"]
    assert staff_client.post("/api/warehouse/pin-reset/verify", json={"code": code}).get_json()["ok"] is True
    assert staff_client.post("/api/warehouse/pin-reset/verify", json={"code": "000000"}).get_json()["ok"] is False


def test_confirm_resets_pin_only_with_valid_code(staff_client):
    _set_pin(staff_client, "111111")
    code = staff_client.post("/api/warehouse/pin-reset/request").get_json()["dev_code"]

    # wrong code -> rejected
    assert staff_client.post("/api/warehouse/pin-reset/confirm",
                             json={"code": "999999", "new_pin": "222222"}).status_code == 403
    # right code, bad pin -> 400
    assert staff_client.post("/api/warehouse/pin-reset/confirm",
                             json={"code": code, "new_pin": "12ab"}).status_code == 400
    # right code, good pin -> resets
    assert staff_client.post("/api/warehouse/pin-reset/confirm",
                             json={"code": code, "new_pin": "222222"}).status_code == 200

    # new PIN works, old one doesn't
    assert staff_client.post("/api/warehouse/verify-pin", json={"pin": "222222"}).get_json()["ok"] is True
    assert staff_client.post("/api/warehouse/verify-pin", json={"pin": "111111"}).get_json()["ok"] is False


def test_code_single_use(staff_client):
    _set_pin(staff_client, "111111")
    code = staff_client.post("/api/warehouse/pin-reset/request").get_json()["dev_code"]
    assert staff_client.post("/api/warehouse/pin-reset/confirm",
                             json={"code": code, "new_pin": "333333"}).status_code == 200
    # same code can't be reused
    assert staff_client.post("/api/warehouse/pin-reset/confirm",
                             json={"code": code, "new_pin": "444444"}).status_code == 403


def test_customer_cannot_request_reset(customer_client):
    assert customer_client.post("/api/warehouse/pin-reset/request").status_code == 403
