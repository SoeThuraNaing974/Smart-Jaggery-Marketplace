-- ============================================================================
-- Smart Jaggery Marketplace — v2 migration (PostgreSQL 14+)
-- Adds expanded-feature columns to existing tables + 8 new tables.
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v2.sql
--
-- Column-name equivalences kept from v1 (NOT renamed, to avoid breaking v1 code):
--   jaggery_batches.batch_id   == spec "batch_code"
--   jaggery_batches.qty_kg     == spec "quantity_kg"
--   order_items.batch_pk       == spec "batch_id" (FK to jaggery_batches.id)
--   order_items.qty_kg         == spec "quantity_kg"
--   order_items.unit_price     == spec "price_per_kg"
--   orders.subtotal            == spec "total_amount"
--   orders.discount_amount     == spec "discount_applied"
--   orders.total_price         == spec "final_amount" (items total after discount)
--   orders.created_at          == spec "order_date"
-- ============================================================================

-- 1) users: contact + address fields ---------------------------------------
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone   VARCHAR(30);
ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS pincode VARCHAR(12);
CREATE INDEX IF NOT EXISTS idx_users_pincode ON users(pincode);

-- 2) warehouses: pincode + manager ----------------------------------------
ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS pincode      VARCHAR(12);
ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS manager_name VARCHAR(120);
CREATE INDEX IF NOT EXISTS idx_warehouses_pincode ON warehouses(pincode);

-- 3) jaggery_batches: active flag -----------------------------------------
ALTER TABLE jaggery_batches ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
CREATE INDEX IF NOT EXISTS idx_batches_active ON jaggery_batches(is_active);

-- 4) orders: delivery charge / pincode / delivered timestamp --------------
ALTER TABLE orders ADD COLUMN IF NOT EXISTS pincode         VARCHAR(12);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_charge NUMERIC(10,2) NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivered_at    TIMESTAMPTZ;

-- 5) wishlist --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wishlist (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    batch_id    INTEGER NOT NULL REFERENCES jaggery_batches(id) ON DELETE CASCADE,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (customer_id, batch_id)
);
CREATE INDEX IF NOT EXISTS idx_wishlist_customer ON wishlist(customer_id);

-- 6) reviews (one per delivered order) ------------------------------------
CREATE TABLE IF NOT EXISTS reviews (
    id           SERIAL PRIMARY KEY,
    order_id     INTEGER NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    customer_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    rating       SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment      TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reviews_warehouse ON reviews(warehouse_id);

-- 7) price_alerts ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS price_alerts (
    id            SERIAL PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    batch_id      INTEGER NOT NULL REFERENCES jaggery_batches(id) ON DELETE CASCADE,
    desired_price NUMERIC(10,2) NOT NULL,
    is_notified   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_price_alerts_batch ON price_alerts(batch_id, is_notified);

-- 8) stock_transfers -------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_transfers (
    id                  SERIAL PRIMARY KEY,
    from_warehouse_id   INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    to_warehouse_id     INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    batch_id            INTEGER NOT NULL REFERENCES jaggery_batches(id) ON DELETE CASCADE,
    quantity_kg         NUMERIC(10,2) NOT NULL CHECK (quantity_kg > 0),
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','approved','rejected','completed')),
    requested_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_by_admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_transfers_status ON stock_transfers(status);

-- 9) delivery_charges (per pincode) ---------------------------------------
CREATE TABLE IF NOT EXISTS delivery_charges (
    id            SERIAL PRIMARY KEY,
    pincode       VARCHAR(12) NOT NULL UNIQUE,
    charge_amount NUMERIC(10,2) NOT NULL DEFAULT 0
);

-- 10) abandoned_carts ------------------------------------------------------
CREATE TABLE IF NOT EXISTS abandoned_carts (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    items_json  JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_abandoned_customer ON abandoned_carts(customer_id, created_at);

-- 11) announcements --------------------------------------------------------
CREATE TABLE IF NOT EXISTS announcements (
    id                 SERIAL PRIMARY KEY,
    title              VARCHAR(160) NOT NULL,
    message            TEXT NOT NULL,
    created_by_admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at         TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_announcements_expires ON announcements(expires_at);

-- 12) audit_logs -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action     VARCHAR(80) NOT NULL,
    details    TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id, created_at);
