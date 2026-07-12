"""Step-up password verification used before confirming a payment."""


def test_verify_password_correct(staff_client):
    r = staff_client.post("/api/verify-password", json={"password": "staff123"})
    assert r.status_code == 200 and r.get_json()["ok"] is True


def test_verify_password_wrong(staff_client):
    r = staff_client.post("/api/verify-password", json={"password": "nope"})
    assert r.status_code == 200 and r.get_json()["ok"] is False


def test_verify_password_requires_login(client):
    assert client.post("/api/verify-password", json={"password": "x"}).status_code == 401
