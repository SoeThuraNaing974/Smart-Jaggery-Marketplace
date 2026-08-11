"""
Consolidated pickup & delivery: splitting, escrow, settlement, edge cases.

The conftest seeds one warehouse, so these tests add two more (B and C) plus a
rider, giving a genuine 3-warehouse basket to split.
"""
from datetime import date, timedelta, datetime

import pytest

from db import db
from models import User, Warehouse, JaggeryBatch, Order
from auth import hash_password
from consolidated.models import (SubOrder, Delivery, DeliveryStop, WarehouseWallet,
                                 PayoutLedger, PlatformLedger, Refund)
from consolidated.money import allocate_proportional, split_order_money, assert_balanced
from decimal import Decimal


# ===================================================================== fixtures
@pytest.fixture
def multi(app):
    """Three warehouses, one batch each (1000/kg), plus an available rider."""
    with app.app_context():
        whs, batches = [], []
        for name, city in (("WH-A", "Yangon"), ("WH-B", "Bago"), ("WH-C", "Mandalay")):
            wh = Warehouse(name=name, location=city, pincode=city)
            db.session.add(wh)
            db.session.flush()
            b = JaggeryBatch(warehouse_id=wh.id, batch_id=f"B-{name}", grade="A",
                             qty_kg=100, harvest_date=date.today() - timedelta(days=5),
                             price_per_kg=1000)
            db.session.add(b)
            whs.append(wh)
            batches.append(b)

        rider = User(name="Rider One", email="rider@t.local",
                     password_hash=hash_password("rider123"), role="rider")
        db.session.add(rider)
        db.session.flush()
        from consolidated.models import RiderProfile
        db.session.add(RiderProfile(user_id=rider.id, base_city="Yangon",
                                    is_available=True, max_active_tasks=5))
        db.session.commit()
        return {"warehouse_ids": [w.id for w in whs],
                "batch_ids": [b.id for b in batches],
                "rider_id": rider.id}


def _client(app, email, password):
    c = app.test_client()
    r = c.post("/api/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.get_json()
    return c


@pytest.fixture
def rider_client(app, multi):
    return _client(app, "rider@t.local", "rider123")


def _wh_client(app, warehouse_id, tag):
    """A warehouse login bound to one specific warehouse."""
    with app.app_context():
        email = f"wh{tag}@t.local"
        if not User.query.filter_by(email=email).first():
            db.session.add(User(name=f"Staff {tag}", email=email,
                                password_hash=hash_password("wh12345"),
                                role="warehouse", warehouse_id=warehouse_id))
            db.session.commit()
    return _client(app, f"wh{tag}@t.local", "wh12345")


def _age_deadline(sub_order_id, *, minutes):
    """
    Push a sub-order's prep deadline into the past so the SLA sweep sees it as late.

    Written through the SAME session the test client uses: the `app` fixture keeps
    one app context alive for the whole test, so requests share that session. A
    nested `with app.app_context()` would commit through a second session and
    leave this one holding a cached row with the old deadline.
    """
    sub = db.session.get(SubOrder, sub_order_id)
    sub.prep_deadline_at = datetime.utcnow() - timedelta(minutes=minutes)
    db.session.commit()
    db.session.expire_all()


def _checkout(customer_client, batch_ids, qty=2, pay=True, **extra):
    body = {
        "items": [{"batch_pk": b, "qty_kg": qty} for b in batch_ids],
        "delivery_address": "Ward 5, No. 23",
        "location": "Yangon",
        "delivery_scope": "local",
        "pay_now": pay,
        "payment_method": "kpay",
    }
    body.update(extra)
    r = customer_client.post("/api/checkout", json=body)
    assert r.status_code in (200, 201), r.get_json()
    return r.get_json()


# ============================================================ 1) money maths
def test_allocation_never_loses_or_invents_kyats():
    assert allocate_proportional(1000, [500, 300, 200]) == [500, 300, 200]
    # 100 / 3 cannot divide evenly — largest remainder keeps the total exact
    assert sum(allocate_proportional(100, [1, 1, 1])) == 100
    assert allocate_proportional(100, [1, 1, 1]) == [34, 33, 33]
    assert sum(allocate_proportional(5000, [7, 11, 13])) == 5000
    assert allocate_proportional(0, [5, 5]) == [0, 0]
    assert allocate_proportional(90, [0, 0, 0]) == [30, 30, 30]   # even fallback


def test_split_reconciles_with_what_the_customer_pays():
    groups = [{"warehouse_id": 1, "goods_subtotal": 12000, "rate": None},
              {"warehouse_id": 2, "goods_subtotal": 8000, "rate": None},
              {"warehouse_id": 3, "goods_subtotal": 5000, "rate": Decimal("0.10")}]
    parts = split_order_money(groups, discount_total=2500, delivery_total=4000,
                              default_rate=Decimal("0.05"))
    assert_balanced(parts, 25000, 2500, 4000)
    assert sum(p.customer_charged for p in parts) == 25000 - 2500 + 4000
    # the per-warehouse override is honoured, not the platform default
    assert parts[2].commission_rate == Decimal("0.10")
    for p in parts:
        assert p.net_payout + p.commission_amount == p.customer_charged


# ================================================ 2) checkout → split → escrow
def test_checkout_splits_one_cart_into_one_sub_order_per_warehouse(customer_client, multi):
    body = _checkout(customer_client, multi["batch_ids"], qty=2)

    assert body["warehouse_count"] == 3
    assert len(body["sub_orders"]) == 3
    assert [s["sub_order_no"][-1] for s in body["sub_orders"]] == ["A", "B", "C"]

    # 3 warehouses × 2kg × 1000 = 6000 goods; promotion applies at 6kg
    assert body["order"]["subtotal"] == 6000
    charged = sum(s["customer_charged"] for s in body["sub_orders"])
    assert charged == body["charged_total"]
    # the parent's money equals the sum of its children, to the Kyat
    assert charged == (body["order"]["subtotal"]
                       - body["order"]["discount_amount"]
                       + body["order"]["delivery_charge"])
    # one delivery fee, shared — not charged three times
    assert sum(s["delivery_share"] for s in body["sub_orders"]) == \
        body["order"]["delivery_charge"]


def test_payment_holds_escrow_and_credits_pending_only(customer_client, multi, app):
    body = _checkout(customer_client, multi["batch_ids"])
    assert body["escrow_status"] == "held"
    assert body["order"]["payment_status"] == "paid"

    with app.app_context():
        for sub in SubOrder.query.all():
            wallet = WarehouseWallet.query.filter_by(warehouse_id=sub.warehouse_id).first()
            # earned but NOT withdrawable until delivery
            assert round(float(wallet.pending_balance)) == round(float(sub.net_payout))
            assert round(float(wallet.available_balance)) == 0
        escrow = PlatformLedger.query.filter_by(entry_type="escrow_in").one()
        assert round(float(escrow.amount)) == body["charged_total"]


def test_checkout_is_idempotent_on_client_token(customer_client, multi):
    first = _checkout(customer_client, multi["batch_ids"], client_token="tok-1")
    again = _checkout(customer_client, multi["batch_ids"], client_token="tok-1")
    assert first["order"]["id"] == again["order"]["id"]
    assert len(again["sub_orders"]) == 3          # not 6


def test_warehouse_sees_only_its_own_sub_order(customer_client, multi, app):
    _checkout(customer_client, multi["batch_ids"])
    a = _wh_client(app, multi["warehouse_ids"][0], "a")
    rows = a.get("/api/warehouse/sub-orders").get_json()
    assert len(rows) == 1
    assert rows[0]["warehouse_id"] == multi["warehouse_ids"][0]


# ============================================ 3) dispatch gating (all ready?)
def test_rider_is_assigned_only_when_every_warehouse_is_ready(customer_client, multi, app):
    body = _checkout(customer_client, multi["batch_ids"])
    subs = body["sub_orders"]
    clients = [_wh_client(app, multi["warehouse_ids"][i], tag)
               for i, tag in enumerate("abc")]

    r1 = clients[0].patch(f"/api/sub-orders/{subs[0]['id']}/ready-for-pickup").get_json()
    assert r1["dispatched"] is False and len(r1["waiting_on"]) == 2

    r2 = clients[1].patch(f"/api/sub-orders/{subs[1]['id']}/ready-for-pickup").get_json()
    assert r2["dispatched"] is False and len(r2["waiting_on"]) == 1

    r3 = clients[2].patch(f"/api/sub-orders/{subs[2]['id']}/ready-for-pickup").get_json()
    assert r3["dispatched"] is True
    trip = r3["delivery"]
    assert trip["stop_count"] == 3
    assert [s["stop_seq"] for s in trip["stops"]] == [1, 2, 3]
    assert trip["rider_id"] == multi["rider_id"]
    assert trip["status"] == "assigned"

    with app.app_context():
        assert Delivery.query.count() == 1       # ONE trip, not three


def test_a_warehouse_cannot_touch_another_warehouses_sub_order(customer_client, multi, app):
    body = _checkout(customer_client, multi["batch_ids"])
    other = _wh_client(app, multi["warehouse_ids"][1], "b")
    r = other.patch(f"/api/sub-orders/{body['sub_orders'][0]['id']}/ready-for-pickup")
    assert r.status_code == 403


# ======================================= 4+5) route, delivery, fund release
def _all_ready(app, multi, subs):
    for i, tag in enumerate("abc"):
        c = _wh_client(app, multi["warehouse_ids"][i], tag)
        c.patch(f"/api/sub-orders/{subs[i]['id']}/ready-for-pickup")


def test_full_happy_path_releases_funds_and_takes_commission(
        customer_client, multi, app, rider_client, admin_client):
    body = _checkout(customer_client, multi["batch_ids"])
    _all_ready(app, multi, body["sub_orders"])

    trip = rider_client.get("/api/rider/tasks").get_json()[0]
    for stop in trip["stops"]:
        r = rider_client.post(
            f"/api/deliveries/{trip['id']}/stops/{stop['id']}/collect")
        assert r.status_code == 200, r.get_json()
    assert r.get_json()["status"] == "out_for_delivery"

    with app.app_context():
        otp = db.session.get(Delivery, trip["id"]).proof_otp
    done = rider_client.post(f"/api/deliveries/{trip['id']}/complete",
                             json={"otp": otp, "note": "handed over"})
    assert done.status_code == 200, done.get_json()
    out = done.get_json()
    assert out["delivery"]["status"] == "delivered"
    assert out["parent"]["order"]["status"] == "delivered"
    assert out["parent"]["escrow_status"] == "released"

    with app.app_context():
        for sub in SubOrder.query.all():
            assert sub.status == "delivered"
            wallet = WarehouseWallet.query.filter_by(warehouse_id=sub.warehouse_id).first()
            # pending emptied, available funded — exactly the net payout
            assert round(float(wallet.pending_balance)) == 0
            assert round(float(wallet.available_balance)) == round(float(sub.net_payout))
            # 5% of the sub-order, per the configured platform rate
            assert round(float(sub.commission_amount)) == \
                round(round(float(sub.customer_charged)) * 0.05)

    escrow = admin_client.get("/api/admin/escrow").get_json()
    assert escrow["commission_earned"] > 0
    assert escrow["warehouse_pending_total"] == 0
    assert escrow["warehouse_available_total"] > 0


def test_completing_twice_never_pays_twice(customer_client, multi, app, rider_client):
    body = _checkout(customer_client, multi["batch_ids"])
    _all_ready(app, multi, body["sub_orders"])
    trip = rider_client.get("/api/rider/tasks").get_json()[0]
    for stop in trip["stops"]:
        rider_client.post(f"/api/deliveries/{trip['id']}/stops/{stop['id']}/collect")
    with app.app_context():
        otp = db.session.get(Delivery, trip["id"]).proof_otp

    first = rider_client.post(f"/api/deliveries/{trip['id']}/complete", json={"otp": otp})
    second = rider_client.post(f"/api/deliveries/{trip['id']}/complete", json={"otp": otp})
    assert first.get_json()["changed"] is True
    assert second.get_json()["changed"] is False       # idempotent, not an error

    with app.app_context():
        # one release entry per sub-order, ever
        assert PayoutLedger.query.filter_by(entry_type="release_available").count() == 3
        for w in WarehouseWallet.query.all():
            sub = SubOrder.query.filter_by(warehouse_id=w.warehouse_id).first()
            assert round(float(w.available_balance)) == round(float(sub.net_payout))


def test_cannot_complete_before_every_stop_is_handled(customer_client, multi, app, rider_client):
    body = _checkout(customer_client, multi["batch_ids"])
    _all_ready(app, multi, body["sub_orders"])
    trip = rider_client.get("/api/rider/tasks").get_json()[0]
    rider_client.post(f"/api/deliveries/{trip['id']}/stops/{trip['stops'][0]['id']}/collect")
    r = rider_client.post(f"/api/deliveries/{trip['id']}/complete")
    assert r.status_code == 422
    assert "not collected" in r.get_json()["error"]


# ================================== EDGE CASE 1 — partial cancellation
def test_one_warehouse_cancels_others_continue(customer_client, multi, app, rider_client):
    body = _checkout(customer_client, multi["batch_ids"])
    subs = body["sub_orders"]
    cancelled_sub = subs[2]

    with app.app_context():
        stock_before = float(db.session.get(JaggeryBatch, multi["batch_ids"][2]).qty_kg)

    c = _wh_client(app, multi["warehouse_ids"][2], "c")
    r = c.post(f"/api/sub-orders/{cancelled_sub['id']}/cancel",
               json={"reason": "out of stock"})
    assert r.status_code == 200, r.get_json()
    out = r.get_json()

    assert out["sub_order"]["status"] == "cancelled"
    # customer refunded exactly that slice — goods + its share of shipping
    assert out["refund"]["amount"] == cancelled_sub["customer_charged"]
    # siblings untouched
    assert [s["status"] for s in out["parent"]["sub_orders"][:2]] == ["preparing", "preparing"]
    assert out["parent"]["order"]["status"] == "waiting"

    with app.app_context():
        # stock went back on the shelf
        assert float(db.session.get(JaggeryBatch, multi["batch_ids"][2]).qty_kg) == \
            stock_before + 2
        # that warehouse's pending credit was reversed to zero
        w = WarehouseWallet.query.filter_by(warehouse_id=multi["warehouse_ids"][2]).first()
        assert round(float(w.pending_balance)) == 0
        # the other two still hold their earnings
        for wid in multi["warehouse_ids"][:2]:
            assert round(float(WarehouseWallet.query.filter_by(
                warehouse_id=wid).first().pending_balance)) > 0

    # the remaining two can now complete the trip on their own
    for i, tag in enumerate("ab"):
        _wh_client(app, multi["warehouse_ids"][i], tag).patch(
            f"/api/sub-orders/{subs[i]['id']}/ready-for-pickup")
    trip = rider_client.get("/api/rider/tasks").get_json()[0]
    assert trip["stop_count"] == 2            # rider visits 2 warehouses, not 3
    for stop in trip["stops"]:
        rider_client.post(f"/api/deliveries/{trip['id']}/stops/{stop['id']}/collect")
    with app.app_context():
        otp = db.session.get(Delivery, trip["id"]).proof_otp
    done = rider_client.post(f"/api/deliveries/{trip['id']}/complete", json={"otp": otp})
    assert done.get_json()["parent"]["order"]["status"] == "delivered"


def test_all_warehouses_cancel_cancels_the_parent(customer_client, multi, app):
    body = _checkout(customer_client, multi["batch_ids"])
    for i, tag in enumerate("abc"):
        c = _wh_client(app, multi["warehouse_ids"][i], tag)
        c.post(f"/api/sub-orders/{body['sub_orders'][i]['id']}/cancel",
               json={"reason": "closed"})
    with app.app_context():
        order = db.session.get(Order, body["order"]["id"])
        assert order.status == "cancelled"
        assert order.escrow_status == "refunded"
        assert round(float(order.refunded_total)) == body["charged_total"]


def test_cannot_cancel_after_pickup(customer_client, multi, app, rider_client):
    body = _checkout(customer_client, multi["batch_ids"])
    _all_ready(app, multi, body["sub_orders"])
    trip = rider_client.get("/api/rider/tasks").get_json()[0]
    rider_client.post(f"/api/deliveries/{trip['id']}/stops/{trip['stops'][0]['id']}/collect")
    picked = trip["stops"][0]["sub_order_id"]
    admin_wh = _wh_client(app, trip["stops"][0]["warehouse_id"], "z")
    r = admin_wh.post(f"/api/sub-orders/{picked}/cancel", json={"reason": "oops"})
    assert r.status_code == 422
    assert "already left the warehouse" in r.get_json()["error"]


# ======================================= EDGE CASE 2 — partial refunds
def test_partial_refund_touches_only_its_sub_order(customer_client, multi, app, admin_client):
    body = _checkout(customer_client, multi["batch_ids"])
    target = body["sub_orders"][1]

    r = admin_client.post(f"/api/admin/sub-orders/{target['id']}/refund",
                          json={"amount": 500, "reason": "0.5kg short"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["refund"]["kind"] == "partial"
    assert r.get_json()["sub_order"]["refunded_amount"] == 500

    with app.app_context():
        sub = db.session.get(SubOrder, target["id"])
        assert sub.status == "preparing"                     # still fulfilling
        w = WarehouseWallet.query.filter_by(warehouse_id=sub.warehouse_id).first()
        # the warehouse carries the refund, from its pending balance
        assert round(float(w.pending_balance)) == round(float(sub.net_payout)) - 500
        # siblings' wallets untouched
        for wid in (multi["warehouse_ids"][0], multi["warehouse_ids"][2]):
            other = SubOrder.query.filter_by(warehouse_id=wid).first()
            ow = WarehouseWallet.query.filter_by(warehouse_id=wid).first()
            assert round(float(ow.pending_balance)) == round(float(other.net_payout))
        order = db.session.get(Order, body["order"]["id"])
        assert round(float(order.refunded_total)) == 500
        assert order.status == "waiting"                     # parent unaffected


def test_refund_cannot_exceed_the_sub_order(customer_client, multi, admin_client):
    body = _checkout(customer_client, multi["batch_ids"])
    target = body["sub_orders"][0]
    r = admin_client.post(f"/api/admin/sub-orders/{target['id']}/refund",
                          json={"amount": target["customer_charged"] + 1})
    assert r.status_code == 400
    assert "exceeds" in r.get_json()["error"]


def test_refund_after_delivery_debits_available_balance(
        customer_client, multi, app, rider_client, admin_client):
    body = _checkout(customer_client, multi["batch_ids"])
    _all_ready(app, multi, body["sub_orders"])
    trip = rider_client.get("/api/rider/tasks").get_json()[0]
    for stop in trip["stops"]:
        rider_client.post(f"/api/deliveries/{trip['id']}/stops/{stop['id']}/collect")
    with app.app_context():
        otp = db.session.get(Delivery, trip["id"]).proof_otp
    rider_client.post(f"/api/deliveries/{trip['id']}/complete", json={"otp": otp})

    target = body["sub_orders"][0]
    admin_client.post(f"/api/admin/sub-orders/{target['id']}/refund",
                      json={"amount": 300, "reason": "quality complaint"})
    with app.app_context():
        sub = db.session.get(SubOrder, target["id"])
        w = WarehouseWallet.query.filter_by(warehouse_id=sub.warehouse_id).first()
        assert round(float(w.available_balance)) == round(float(sub.net_payout)) - 300
        assert PayoutLedger.query.filter_by(entry_type="debit_available").count() == 1


# ================================ EDGE CASE 3 — slow warehouse / rider delay
def test_sla_sweep_dispatches_partially_when_one_warehouse_is_late(
        customer_client, multi, app, admin_client, rider_client):
    body = _checkout(customer_client, multi["batch_ids"])
    subs = body["sub_orders"]
    # A and B are ready; C is silent
    for i, tag in enumerate("ab"):
        _wh_client(app, multi["warehouse_ids"][i], tag).patch(
            f"/api/sub-orders/{subs[i]['id']}/ready-for-pickup")

    _age_deadline(subs[2]["id"], minutes=45)          # past the dispatch grace

    report = admin_client.post("/api/ops/prep-sla-sweep").get_json()
    assert len(report["dispatch_partial"]) == 1
    assert report["dispatch_partial"][0]["left_behind"] == [subs[2]["sub_order_no"]]

    trip = rider_client.get("/api/rider/tasks").get_json()[0]
    assert trip["is_partial"] is True
    assert trip["stop_count"] == 2            # goes with what exists

    # C catches up later → it gets its own follow-up trip, not a lost order
    _wh_client(app, multi["warehouse_ids"][2], "c").patch(
        f"/api/sub-orders/{subs[2]['id']}/ready-for-pickup")
    with app.app_context():
        assert Delivery.query.count() == 2
        assert DeliveryStop.query.filter_by(sub_order_id=subs[2]["id"]).count() == 1


def test_sla_sweep_auto_cancels_past_the_hard_deadline(customer_client, multi, app, admin_client):
    body = _checkout(customer_client, multi["batch_ids"])
    subs = body["sub_orders"]
    _age_deadline(subs[2]["id"], minutes=300)          # past the hard deadline

    report = admin_client.post("/api/ops/prep-sla-sweep").get_json()
    assert report["auto_cancel"] and \
        report["auto_cancel"][0]["cancelled"] == [subs[2]["sub_order_no"]]
    with app.app_context():
        assert db.session.get(SubOrder, subs[2]["id"]).status == "cancelled"
        assert Refund.query.filter_by(sub_order_id=subs[2]["id"]).count() == 1


def test_rider_can_skip_a_warehouse_that_is_not_packed(customer_client, multi, app, rider_client):
    body = _checkout(customer_client, multi["batch_ids"])
    _all_ready(app, multi, body["sub_orders"])
    trip = rider_client.get("/api/rider/tasks").get_json()[0]

    rider_client.post(f"/api/deliveries/{trip['id']}/stops/{trip['stops'][0]['id']}/collect")
    skipped_sub = trip["stops"][1]["sub_order_id"]
    r = rider_client.post(f"/api/deliveries/{trip['id']}/stops/{trip['stops'][1]['id']}/skip",
                          json={"reason": "not packed on arrival"})
    assert r.status_code == 200, r.get_json()
    rider_client.post(f"/api/deliveries/{trip['id']}/stops/{trip['stops'][2]['id']}/collect")

    with app.app_context():
        # the skipped sub-order is back in the pool, free for a follow-up trip
        sub = db.session.get(SubOrder, skipped_sub)
        assert sub.status == "preparing"
        assert DeliveryStop.query.filter_by(sub_order_id=skipped_sub).count() == 0

    with app.app_context():
        otp = db.session.get(Delivery, trip["id"]).proof_otp
    done = rider_client.post(f"/api/deliveries/{trip['id']}/complete", json={"otp": otp})
    assert done.status_code == 200, done.get_json()
    # parent stays open because one warehouse still owes goods
    assert done.get_json()["parent"]["order"]["status"] != "delivered"


# ==================================================== wallets & withdrawals
def test_withdraw_limited_to_available_balance(customer_client, multi, app, rider_client):
    body = _checkout(customer_client, multi["batch_ids"])
    _all_ready(app, multi, body["sub_orders"])
    trip = rider_client.get("/api/rider/tasks").get_json()[0]
    for stop in trip["stops"]:
        rider_client.post(f"/api/deliveries/{trip['id']}/stops/{stop['id']}/collect")
    with app.app_context():
        otp = db.session.get(Delivery, trip["id"]).proof_otp
    rider_client.post(f"/api/deliveries/{trip['id']}/complete", json={"otp": otp})

    a = _wh_client(app, multi["warehouse_ids"][0], "a")
    wallet = a.get("/api/warehouse/wallet").get_json()["wallet"]
    assert wallet["available_balance"] > 0

    too_much = a.post("/api/warehouse/wallet/withdraw",
                      json={"amount": wallet["available_balance"] + 1})
    assert too_much.status_code == 400

    ok = a.post("/api/warehouse/wallet/withdraw", json={"amount": 100})
    assert ok.status_code == 200
    assert ok.get_json()["available_balance"] == wallet["available_balance"] - 100
    assert ok.get_json()["withdrawn_total"] == 100
