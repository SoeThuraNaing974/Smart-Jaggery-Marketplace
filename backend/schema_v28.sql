-- ===========================================================================
-- v28 migration — Consolidated Pickup & Delivery with Multi-Warehouse Splitting
--
--   orders (PARENT)            one customer payment, held in platform escrow
--     └── sub_orders (CHILD)   one per warehouse, own money + own status
--           └── order_items    items belong to a parent AND to one sub-order
--     └── deliveries           one consolidated rider trip
--           └── delivery_stops one stop per warehouse, in route sequence
--
--   warehouse_wallets  pending → available balances
--   payout_ledgers     append-only money journal (idempotent, auditable)
--   platform_ledgers   escrow in / commission earned / payout out / refund out
--   refunds            per-sub-order refunds (partial refunds never touch siblings)
--
-- Money is whole Kyats. Amounts are NUMERIC(12,2) to match the existing tables,
-- but every calculation is done in integer Kyats so splits always add back up.
-- Idempotent: safe to run more than once.
-- ===========================================================================

BEGIN;

-- ---------------------------------------------------------------- 1) roles
-- The rider is a new role. users.role is guarded by a CHECK, so it is replaced.
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD  CONSTRAINT users_role_check
    CHECK (role IN ('customer', 'warehouse', 'admin', 'rider'));

-- Rider profile (1:1 with a users row of role='rider').
CREATE TABLE IF NOT EXISTS rider_profiles (
    user_id      INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    vehicle_type VARCHAR(20)  NOT NULL DEFAULT 'motorbike',  -- motorbike|van|truck
    plate_no     VARCHAR(30),
    base_city    VARCHAR(60),          -- matched against the delivery location
    is_available BOOLEAN      NOT NULL DEFAULT TRUE,
    max_active_tasks SMALLINT NOT NULL DEFAULT 1,   -- concurrent consolidated trips
    rating       NUMERIC(3,2),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rider_available ON rider_profiles(is_available, base_city);

-- ------------------------------------------------- 2) parent order additions
-- client_token makes checkout idempotent: a double-tapped "Place order" that
-- retries with the same token returns the FIRST order instead of duplicating it.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS client_token    VARCHAR(64);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS refunded_total  NUMERIC(12,2) NOT NULL DEFAULT 0;
-- none → held (customer paid, platform holds it) → released / refunded
ALTER TABLE orders ADD COLUMN IF NOT EXISTS escrow_status   VARCHAR(20)   NOT NULL DEFAULT 'none';
CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_client_token
    ON orders(client_token) WHERE client_token IS NOT NULL;

-- The parent now travels further than the old 4 states: it must be able to reach
-- 'out_for_delivery' and 'delivered'. Superset of the old list, so existing rows
-- stay valid.
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_status_check;
ALTER TABLE orders ADD  CONSTRAINT orders_status_check CHECK (status IN (
    'pending',            -- created, awaiting payment
    'waiting',            -- paid, warehouses preparing
    'assigned',           -- rider assigned to the consolidated route
    'packed',
    'shipped',            -- kept for backwards compatibility
    'out_for_delivery',   -- everything collected, on the way to the customer
    'delivered',
    'cancelled'
));

-- --------------------------------------------------------- 3) sub_orders
CREATE TABLE IF NOT EXISTS sub_orders (
    id            SERIAL PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(id)     ON DELETE CASCADE,
    -- RESTRICT on purpose: a warehouse holding financial history must not be
    -- hard-deleted. Deactivate it instead (see README "Warehouse deletion").
    warehouse_id  INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
    sub_order_no  VARCHAR(32) NOT NULL UNIQUE,     -- e.g. ORD-1001-A
    seq           SMALLINT    NOT NULL,            -- 1,2,3… within the parent

    status        VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- money, all derived at checkout and then FROZEN (never recomputed later)
    goods_subtotal   NUMERIC(12,2) NOT NULL DEFAULT 0,  -- Σ line_total for this warehouse
    discount_share   NUMERIC(12,2) NOT NULL DEFAULT 0,  -- share of the cart promotion
    delivery_share   NUMERIC(12,2) NOT NULL DEFAULT 0,  -- share of the one delivery fee
    customer_charged NUMERIC(12,2) NOT NULL DEFAULT 0,  -- goods - discount + delivery
    commission_rate  NUMERIC(5,4)  NOT NULL DEFAULT 0,  -- snapshot, e.g. 0.0500
    commission_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    net_payout       NUMERIC(12,2) NOT NULL DEFAULT 0,  -- customer_charged - commission
    refunded_amount  NUMERIC(12,2) NOT NULL DEFAULT 0,

    prep_deadline_at TIMESTAMPTZ,      -- SLA for "Ready for Pickup"
    ready_at         TIMESTAMPTZ,
    picked_up_at     TIMESTAMPTZ,
    delivered_at     TIMESTAMPTZ,
    cancelled_at     TIMESTAMPTZ,
    cancel_reason    VARCHAR(200),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT sub_orders_status_chk CHECK (status IN (
        'pending',           -- awaiting payment
        'preparing',         -- paid; warehouse is packing
        'ready_for_pickup',
        'picked_up',
        'delivered',
        'cancelled'
    )),
    CONSTRAINT sub_orders_money_chk CHECK (
        customer_charged = goods_subtotal - discount_share + delivery_share
        AND net_payout   = customer_charged - commission_amount
        AND refunded_amount <= customer_charged
    ),
    -- exactly one sub-order per warehouse per parent order
    CONSTRAINT uq_sub_order_wh UNIQUE (order_id, warehouse_id)
);
CREATE INDEX IF NOT EXISTS idx_sub_orders_order     ON sub_orders(order_id);
CREATE INDEX IF NOT EXISTS idx_sub_orders_wh_status ON sub_orders(warehouse_id, status);
CREATE INDEX IF NOT EXISTS idx_sub_orders_prep_sla  ON sub_orders(prep_deadline_at)
    WHERE status IN ('pending', 'preparing');

-- ------------------------------------------------- 4) items → sub-orders
-- order_items keeps order_id (nothing existing breaks) and gains sub_order_id.
-- Invariant, asserted in code: order_items.order_id = sub_orders.order_id.
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS sub_order_id INTEGER
    REFERENCES sub_orders(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_order_items_sub ON order_items(sub_order_id);

-- --------------------------------------------------------- 5) deliveries
-- One consolidated rider trip: N warehouse pickups → 1 customer drop-off.
CREATE TABLE IF NOT EXISTS deliveries (
    id           SERIAL PRIMARY KEY,
    order_id     INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    rider_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    task_no      VARCHAR(32) NOT NULL UNIQUE,      -- e.g. TRIP-1001-1
    status       VARCHAR(20) NOT NULL DEFAULT 'pending_assignment',
    is_partial   BOOLEAN     NOT NULL DEFAULT FALSE,  -- late warehouse left behind
    stop_count   SMALLINT    NOT NULL DEFAULT 0,
    delivery_fee NUMERIC(12,2) NOT NULL DEFAULT 0,   -- fee the customer paid for this trip
    drop_address TEXT,
    drop_location VARCHAR(60),
    proof_otp    VARCHAR(6),        -- shown to the customer, entered by the rider
    proof_note   VARCHAR(200),
    assigned_at  TIMESTAMPTZ,
    collected_at TIMESTAMPTZ,       -- all stops collected
    delivered_at TIMESTAMPTZ,
    failed_reason VARCHAR(200),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT deliveries_status_chk CHECK (status IN (
        'pending_assignment',  -- route built, no rider free yet
        'assigned',            -- rider has the route
        'collecting',          -- rider started the pickup run
        'collected',           -- all stops collected
        'out_for_delivery',
        'delivered',
        'failed',
        'cancelled'
    ))
);
CREATE INDEX IF NOT EXISTS idx_deliveries_order  ON deliveries(order_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_rider  ON deliveries(rider_id, status);
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries(status);

-- ------------------------------------------------------ 6) delivery_stops
CREATE TABLE IF NOT EXISTS delivery_stops (
    id           SERIAL PRIMARY KEY,
    delivery_id  INTEGER NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
    -- UNIQUE: a sub-order is collected by exactly one trip, ever. This is the
    -- hard guard against two riders being sent for the same goods.
    sub_order_id INTEGER NOT NULL UNIQUE REFERENCES sub_orders(id) ON DELETE CASCADE,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
    stop_seq     SMALLINT    NOT NULL,        -- 1 = first warehouse visited
    status       VARCHAR(20) NOT NULL DEFAULT 'pending',
    arrived_at   TIMESTAMPTZ,
    collected_at TIMESTAMPTZ,
    skip_reason  VARCHAR(200),
    CONSTRAINT delivery_stops_status_chk CHECK (status IN (
        'pending', 'arrived', 'collected', 'skipped'
    )),
    CONSTRAINT uq_stop_seq UNIQUE (delivery_id, stop_seq)
);
CREATE INDEX IF NOT EXISTS idx_stops_delivery ON delivery_stops(delivery_id, stop_seq);

-- --------------------------------------------------- 7) warehouse wallets
CREATE TABLE IF NOT EXISTS warehouse_wallets (
    id                SERIAL PRIMARY KEY,
    warehouse_id      INTEGER NOT NULL UNIQUE REFERENCES warehouses(id) ON DELETE RESTRICT,
    pending_balance   NUMERIC(14,2) NOT NULL DEFAULT 0,  -- earned, not yet delivered
    available_balance NUMERIC(14,2) NOT NULL DEFAULT 0,  -- withdrawable
    withdrawn_total   NUMERIC(14,2) NOT NULL DEFAULT 0,
    lifetime_earned   NUMERIC(14,2) NOT NULL DEFAULT 0,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT wallet_non_negative CHECK (pending_balance >= 0 AND available_balance >= 0)
);

-- ------------------------------------------------------ 8) payout ledger
-- Append-only. The wallet columns are a cached projection of this journal;
-- idempotency_key is what makes "release the money" safe to retry.
CREATE TABLE IF NOT EXISTS payout_ledgers (
    id            BIGSERIAL PRIMARY KEY,
    warehouse_id  INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
    sub_order_id  INTEGER REFERENCES sub_orders(id) ON DELETE SET NULL,
    entry_type    VARCHAR(24) NOT NULL,
    amount        NUMERIC(14,2) NOT NULL,      -- always positive; direction is in entry_type
    pending_delta   NUMERIC(14,2) NOT NULL DEFAULT 0,
    available_delta NUMERIC(14,2) NOT NULL DEFAULT 0,
    pending_after   NUMERIC(14,2) NOT NULL,
    available_after NUMERIC(14,2) NOT NULL,
    idempotency_key VARCHAR(120) NOT NULL UNIQUE,
    note          VARCHAR(200),
    created_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ledger_type_chk CHECK (entry_type IN (
        'credit_pending',    -- payment captured → warehouse earns (pending)
        'release_available', -- delivered      → pending becomes withdrawable
        'reverse_pending',   -- sub-order cancelled before delivery
        'debit_available',   -- refund after the money was already released
        'withdrawal',        -- warehouse withdrew cash
        'adjustment'
    ))
);
CREATE INDEX IF NOT EXISTS idx_ledger_wh   ON payout_ledgers(warehouse_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ledger_sub  ON payout_ledgers(sub_order_id);

-- --------------------------------------------------- 9) platform / escrow
CREATE TABLE IF NOT EXISTS platform_ledgers (
    id            BIGSERIAL PRIMARY KEY,
    order_id      INTEGER REFERENCES orders(id) ON DELETE SET NULL,
    sub_order_id  INTEGER REFERENCES sub_orders(id) ON DELETE SET NULL,
    entry_type    VARCHAR(24) NOT NULL,
    amount        NUMERIC(14,2) NOT NULL,
    escrow_delta  NUMERIC(14,2) NOT NULL DEFAULT 0,   -- +in / -out of escrow
    idempotency_key VARCHAR(120) NOT NULL UNIQUE,
    note          VARCHAR(200),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT platform_type_chk CHECK (entry_type IN (
        'escrow_in',          -- customer paid
        'commission_earned',  -- platform revenue, recognised on delivery
        'payout_released',    -- moved to a warehouse's available balance
        'refund_out',         -- returned to the customer
        'delivery_income'
    ))
);
CREATE INDEX IF NOT EXISTS idx_platform_order ON platform_ledgers(order_id);

-- ------------------------------------------------------------ 10) refunds
CREATE TABLE IF NOT EXISTS refunds (
    id            SERIAL PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    sub_order_id  INTEGER REFERENCES sub_orders(id) ON DELETE SET NULL,  -- NULL = whole order
    amount        NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    reason        VARCHAR(200),
    kind          VARCHAR(20) NOT NULL DEFAULT 'partial',  -- partial | full
    status        VARCHAR(20) NOT NULL DEFAULT 'processed',
    method        VARCHAR(20),
    idempotency_key VARCHAR(120) NOT NULL UNIQUE,
    created_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT refunds_status_chk CHECK (status IN ('pending', 'processed', 'failed'))
);
CREATE INDEX IF NOT EXISTS idx_refunds_order ON refunds(order_id);
CREATE INDEX IF NOT EXISTS idx_refunds_sub   ON refunds(sub_order_id);

-- ------------------------------------ 11) per-warehouse commission override
-- NULL = use the platform default (Config.PLATFORM_COMMISSION_RATE).
ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS commission_rate NUMERIC(5,4);

COMMIT;
