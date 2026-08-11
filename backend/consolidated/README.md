# Consolidated Pickup & Delivery with Multi-Warehouse Order Splitting

One cart spanning several warehouses → one payment into platform escrow → one
parent order split into per-warehouse sub-orders → **one rider** who visits each
warehouse in sequence and makes a single delivery → automatic commission and
wallet settlement on delivery.

Built as an additive package on the existing Flask/SQLAlchemy app. The old
single-warehouse `POST /api/orders` flow is untouched, so nothing in production
changes until the frontend starts calling `/api/checkout`.

| File | What it holds |
|---|---|
| [`../schema_v28.sql`](../schema_v28.sql) | Production DDL: tables, FKs, indexes, CHECK constraints |
| [`money.py`](money.py) | Integer-Kyat allocation — the split maths, no DB |
| [`models.py`](models.py) | SQLAlchemy models |
| [`services.py`](services.py) | All business rules and money movements |
| [`routes.py`](routes.py) | HTTP endpoints (thin) |
| [`settings.py`](settings.py) | Commission %, SLA windows, refund policy (env-driven) |
| [`../tests/test_consolidated.py`](../tests/test_consolidated.py) | 21 tests covering the flow and every edge case |

---

## 1. Data model

```
users ────────────┐ (customer)
                  ▼
           ┌──────────────┐   1 payment, 1 escrow hold, 1 invoice
           │   orders     │   = PARENT ORDER  (existing table, extended)
           └──────┬───────┘
                  │ 1..N  (split by warehouse_id)
           ┌──────▼───────┐   own status, own money, own SLA
           │  sub_orders  │   = CHILD ORDER   ──── warehouses
           └──────┬───────┘
                  │ 1..N
           ┌──────▼───────┐
           │ order_items  │   order_id (parent) + sub_order_id (child)
           └──────────────┘

           ┌──────────────┐   1 consolidated trip per dispatch
  orders ─▶│  deliveries  │──── rider (users.role='rider' + rider_profiles)
           └──────┬───────┘
                  │ 1..N  in visiting order
           ┌──────▼────────┐
           │delivery_stops │  UNIQUE(sub_order_id) ← goods collected once, ever
           └───────────────┘

  warehouses ─1:1─ warehouse_wallets   (pending_balance / available_balance)
                        ▲
                        └── payout_ledgers    append-only, UNIQUE(idempotency_key)
  platform_ledgers   escrow_in / commission_earned / payout_released / refund_out
  refunds            one row per refund, scoped to a single sub_order
```

### Why the existing `orders` table is the parent

`orders` already owns the customer, the single payment, the delivery address and
the invoice, and `order_messages`, `reviews` and the PDF generators all point at
`orders.id`. Making it the parent means **zero** rewrites there. `order_items`
keeps its `order_id` and gains `sub_order_id`, so every existing query keeps
working while new code can group by warehouse.

### Key constraints doing real work

| Constraint | Prevents |
|---|---|
| `sub_orders UNIQUE(order_id, warehouse_id)` | two sub-orders for the same warehouse in one order |
| `sub_orders_money_chk` | a sub-order whose numbers do not balance (`charged = goods − discount + delivery`, `net = charged − commission`) |
| `delivery_stops UNIQUE(sub_order_id)` | two riders dispatched for the same goods |
| `deliveries UNIQUE(task_no)` | duplicate trips from a retried dispatch |
| `payout_ledgers UNIQUE(idempotency_key)` | **paying a warehouse twice** |
| `platform_ledgers UNIQUE(idempotency_key)` | double-counting escrow or commission |
| `refunds UNIQUE(idempotency_key)` | a double-clicked refund going out twice |
| `wallet_non_negative` | a wallet going below zero, ever |
| `warehouse_id … ON DELETE RESTRICT` | deleting a warehouse that holds financial history |

---

## 2. The money split (the part that is easy to get wrong)

The customer pays **one** delivery fee and gets **one** cart promotion. Both must
be shared across warehouses so that the sub-orders add back up to exactly what
was charged.

Naive per-warehouse `round()` loses or invents Kyats. [`money.py`](money.py) uses
the **largest-remainder method** in integers:

```python
allocate_proportional(100, [1, 1, 1])   # → [34, 33, 33], sums to exactly 100
allocate_proportional(5000, [7, 11, 13])  # → sums to exactly 5000
```

Per sub-order, all in whole Kyats:

```
goods_subtotal    Σ line totals for that warehouse
discount_share    share of the cart promotion   (weighted by goods)
delivery_share    share of the ONE delivery fee (weighted by goods)
customer_charged  goods_subtotal − discount_share + delivery_share
commission_amount round(customer_charged × commission_rate)     ← 5% default
net_payout        customer_charged − commission_amount
```

`assert_balanced()` runs inside the checkout transaction: if the children do not
sum to the parent, the order is rolled back rather than committed wrong.

The **rate is snapshotted** onto the sub-order at checkout. Raising the platform
commission next month must never retroactively change what an old order paid.
`warehouses.commission_rate` overrides the platform default per warehouse; both
are read once, at checkout.

---

## 3. Flow, step by step

### Step 1 — `POST /api/checkout` (customer)

```json
{ "items": [{"batch_pk": 11, "qty_kg": 2}, {"batch_pk": 24, "qty_kg": 3}],
  "delivery_address": "Ward 5, No. 23", "location": "Yangon",
  "delivery_scope": "local", "payment_method": "kpay",
  "pay_now": true, "client_token": "uuid-v4" }
```

1. Locks every batch **in ascending id order** (`SELECT … FOR UPDATE`) so two
   simultaneous carts cannot oversell the same stock, and cannot deadlock.
2. Validates expiry / active / stock per line.
3. Prices goods and the promotion with the existing `services.price_order`.
4. Delivery fee comes from the admin's `delivery_charges` table for the chosen
   city (the same lookup the cart page shows).
5. Splits the money, asserts it balances.
6. Creates the parent, the sub-orders (`ORD-1001-A`, `-B`, `-C`), the items, and
   decrements stock.

`client_token` makes this **idempotent**: a double-tapped "Place order" returns
the first order instead of charging twice.

### Step 1c — payment lands in escrow

`capture_payment()` (via `pay_now`, or `POST /api/orders/<id>/capture-payment`,
or a gateway webhook):

* `orders.escrow_status = 'held'`, `platform_ledgers += escrow_in`
* every sub-order → `preparing`, with `prep_deadline_at = now + PREP_WINDOW_HOURS`
* every warehouse's `net_payout` → **pending_balance** (earned, not withdrawable)

### Step 3 — `GET /api/warehouse/sub-orders`, `PATCH /api/sub-orders/<id>/ready-for-pickup`

A warehouse login can only ever see rows for its own `warehouse_id` — there is no
parameter that widens the filter, and marking someone else's sub-order ready
returns **403**.

The PATCH response tells the warehouse exactly where the order stands:

```json
{ "changed": true, "dispatched": false, "waiting_on": ["ORD-1001-C"] }
```

### Step 4 — dispatch: one rider, sequential pickups

`try_dispatch()` runs after every readiness change and creates the trip **only
when every open sub-order is ready**. Then:

* `plan_route()` orders the stops (`stop_seq` 1…N). It is deliberately a simple,
  swappable sort — drop in an OSRM/Google distance matrix without touching
  anything else.
* `pick_rider()` picks the least-loaded available rider, preferring one based in
  the delivery city. No rider free → the trip waits as `pending_assignment`.

Concurrency: two warehouses can click "Ready" in the same millisecond. The parent
order row is locked first, and `UNIQUE(delivery_stops.sub_order_id)` is the
backstop — a second trip for the same goods cannot commit. The test
`test_rider_is_assigned_only_when_every_warehouse_is_ready` asserts exactly one
`Delivery` row after three concurrent-ish readiness calls.

Rider endpoints: `GET /api/rider/tasks`, then per stop
`…/arrive`, `…/collect`, `…/skip`. When the last stop is collected the trip flips
to `out_for_delivery` and the parent order follows.

### Step 5 — `POST /api/deliveries/<id>/complete` (rider)

Inside one transaction:

* every collected sub-order → `delivered`
* `pending_balance → available_balance` per warehouse, keyed
  `release:sub_order:<id>`
* `platform_ledgers += commission_earned` and `payout_released` (escrow out)
* the parent closes only when no sub-order is still open

Calling it twice returns `{"changed": false}` and pays nobody twice —
`test_completing_twice_never_pays_twice` asserts exactly three
`release_available` ledger rows for a 3-warehouse order after two calls.

---

## 4. Edge cases

### 4a. Partial cancellation — 1 of 3 warehouses goes out of stock

`POST /api/sub-orders/<id>/cancel`

1. **Restock** that warehouse's items (locked per batch).
2. **Reverse** its pending wallet credit (`reverse:sub_order:<id>`) — nothing was
   released yet, so pending simply goes back to zero.
3. **Refund** the customer that slice only: goods + *its* delivery share, because
   they received less service. `REFUND_DELIVERY_SHARE_ON_PARTIAL=false` keeps the
   shipping if you prefer the trip-still-happened policy.
4. **Reroute**: the stop is deleted, remaining stops resequenced 1…n, the trip's
   fee reduced. Deleting the stop frees `UNIQUE(sub_order_id)`.
5. If it was the last open sub-order → parent `cancelled`, escrow `refunded`.
6. Otherwise `try_dispatch()` runs again — the remaining two may now be complete,
   so the rider leaves immediately instead of waiting for a warehouse that is
   never coming.

Siblings are untouched: their statuses, wallets and payouts do not move. After
pickup, cancellation is refused (`422 "goods already left the warehouse"`) — that
is a return, not a cancellation.

### 4b. Partial refund on one sub-order

`POST /api/admin/sub-orders/<id>/refund  { "amount": 500, "reason": "0.5kg short" }`

* capped at `refundable_amount` (`customer_charged − already refunded`), so a
  refund can never exceed the slice → `400`
* **not yet delivered** → clawed back from that warehouse's *pending* balance
* **already delivered** → debited from its *available* balance
  (`debit_available`)
* `platform_ledgers += refund_out` reduces escrow; `orders.refunded_total` grows
  so invoices and reports stay truthful
* the parent order's status never changes, and no sibling wallet moves

Ledger entries are keyed `refund:sub_order:<id>:<n>`, so a retried request is a
no-op that returns the original refund row.

### 4c. Rider delay / one slow warehouse

Two layers.

**Before the rider leaves** — `POST /api/ops/prep-sla-sweep` (point cron at it
every few minutes). `evaluate_prep_sla()` returns one of:

| Verdict | When | Action |
|---|---|---|
| `wait` | inside `PREP_WINDOW_HOURS` | nothing |
| `nudge` | deadline passed | notify the warehouse |
| `dispatch_partial` | deadline + `PARTIAL_DISPATCH_AFTER_MINUTES` (30) and someone is ready | rider leaves with what exists; the late sub-order is flagged `is_partial` and picked up on a **follow-up trip** when it is ready |
| `auto_cancel` | deadline + `AUTO_CANCEL_AFTER_MINUTES` (180) | cancel that sub-order, refund the slice, let the rest go |

**After the rider arrives** — `POST /api/deliveries/<id>/stops/<sid>/skip`. The
warehouse is not packed, so the rider does not sit there: the stop is removed,
the sub-order returns to `preparing` (back in the pool for a follow-up trip), and
the trip continues with the rest. The parent order stays open until that
warehouse's goods are delivered.

---

## 5. Configuration

| Env var | Default | Meaning |
|---|---|---|
| `PLATFORM_COMMISSION_RATE` | `0.05` | 5%; per-warehouse override in `warehouses.commission_rate` |
| `COMMISSION_ON_DELIVERY` | `true` | commission on goods + shipping share (spec) vs goods only |
| `REFUND_DELIVERY_SHARE_ON_PARTIAL` | `true` | refund the cancelled slice's shipping |
| `PREP_WINDOW_HOURS` | `4` | time to reach "Ready for Pickup" |
| `PARTIAL_DISPATCH_AFTER_MINUTES` | `30` | grace before the rider leaves without a late warehouse |
| `AUTO_CANCEL_AFTER_MINUTES` | `180` | hard deadline before auto-cancel + refund |
| `REQUIRE_DELIVERY_OTP` | `true` | rider must enter the customer's 6-digit code |

`GET /api/ops/settings` returns the effective values.

---

## 6. Operational notes

* **Migration**: `psql -f backend/schema_v28.sql` (idempotent). Already applied to
  the local dev database.
* **Warehouse deletion**: `sub_orders.warehouse_id` is `ON DELETE RESTRICT`, so
  the existing `_purge_warehouse()` hard delete in `routes/admin.py` will now fail
  for any warehouse with order history. That is deliberate — deleting a warehouse
  that has been paid would orphan financial records. Deactivate (`blocked`)
  instead, or add an explicit archive step.
* **Riders**: create a `users` row with `role='rider'` plus a `rider_profiles`
  row. `users_role_check` was extended to allow the new role.
* **Ledger is the truth**: `warehouse_wallets` is a cached projection. To audit,
  sum `payout_ledgers.pending_delta` / `available_delta` per warehouse and compare
  — they must match the wallet columns exactly.
* **Not yet built** (deliberately out of scope of the backend deliverable): the
  EJS screens for the rider app, the warehouse sub-order list, and the admin
  escrow dashboard. Every endpoint they need exists and is tested.
