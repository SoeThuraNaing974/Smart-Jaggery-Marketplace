"""Smoke tests for v3: per-order messaging + bulk email (dry-run)."""


def _ordered(customer_client, admin_client):
    bid = next(b["id"] for b in customer_client.get("/api/batches").get_json()
               if b["batch_id"] == "B-FRESH")
    oid = customer_client.post("/api/orders", json={
        "delivery_address": "x", "items": [{"batch_pk": bid, "qty_kg": 2}]
    }).get_json()["order"]["id"]
    admin_client.post(f"/api/admin/orders/{oid}/assign", json={"warehouse_id": 1})
    return oid


def test_message_thread(customer_client, admin_client, staff_client):
    oid = _ordered(customer_client, admin_client)
    assert customer_client.post(f"/api/orders/{oid}/messages",
                                json={"message": "hi"}).status_code == 201
    assert staff_client.post(f"/api/orders/{oid}/messages",
                             json={"message": "ships tomorrow"}).status_code == 201
    thread = staff_client.get(f"/api/orders/{oid}/messages").get_json()
    assert [m["sender_role"] for m in thread] == ["customer", "warehouse"]


def test_message_empty_rejected(customer_client, admin_client):
    oid = _ordered(customer_client, admin_client)
    assert customer_client.post(f"/api/orders/{oid}/messages", json={"message": "   "}).status_code == 400


def test_message_access_denied_for_unrelated_order(customer_client):
    # a customer cannot message an order that doesn't exist / isn't theirs
    assert customer_client.get("/api/orders/999999/messages").status_code == 404


def test_bulk_email_dry_run(admin_client):
    r = admin_client.post("/api/admin/email/bulk",
                          json={"subject": "Hi", "body": "Fresh jaggery!"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "dry_run"  # no SMTP configured in tests


def test_bulk_email_validation(admin_client):
    assert admin_client.post("/api/admin/email/bulk", json={"subject": ""}).status_code == 400
