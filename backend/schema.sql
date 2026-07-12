-- ============================================================================
-- Smart Jaggery Marketplace — PostgreSQL schema (PostgreSQL 14+)
-- Run once:  psql -U postgres -d jaggery_db -f schema.sql
-- NOTE: The Flask app uses SQLAlchemy models (models.py) that map 1:1 to these
--       tables. This file is the canonical reference + lets you bootstrap the DB
--       without running Python. Pick ONE: either run this file OR let the app
--       call db.create_all(). They produce equivalent tables.
-- ============================================================================

-- Role / grade / status are constrained with CHECK + VARCHAR (not native ENUM
-- types) so they line up exactly with the SQLAlchemy String columns the app
-- uses, and so db.create_all() can also build these tables standalone.

-- Warehouses ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS warehouses (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    location    VARCHAR(200) NOT NULL,
    phone       VARCHAR(30),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Users (customers, warehouse staff, admins) --------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    email         VARCHAR(160) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'customer'
                  CHECK (role IN ('customer', 'warehouse', 'admin')),
    -- staff belong to exactly one warehouse; NULL for customers/admins
    warehouse_id  INTEGER REFERENCES warehouses(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- guard: only warehouse may carry a warehouse_id
    CONSTRAINT chk_staff_warehouse
        CHECK (role = 'warehouse' OR warehouse_id IS NULL)
);
CREATE INDEX IF NOT EXISTS idx_users_role         ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_warehouse_id ON users(warehouse_id);

-- Jaggery batches ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS jaggery_batches (
    id               SERIAL PRIMARY KEY,
    warehouse_id     INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    batch_id         VARCHAR(60) NOT NULL UNIQUE,        -- human/business id, e.g. JAG-2026-001
    grade            VARCHAR(1) NOT NULL CHECK (grade IN ('A', 'B', 'C')),
    qty_kg           NUMERIC(10,2) NOT NULL CHECK (qty_kg >= 0),
    harvest_date     DATE NOT NULL,
    price_per_kg     NUMERIC(10,2) NOT NULL CHECK (price_per_kg >= 0),
    certificate_path VARCHAR(255),                       -- local path to PDF
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_batches_warehouse ON jaggery_batches(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_batches_harvest   ON jaggery_batches(harvest_date);
CREATE INDEX IF NOT EXISTS idx_batches_grade     ON jaggery_batches(grade);

-- Orders -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id                   SERIAL PRIMARY KEY,
    customer_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_warehouse_id INTEGER REFERENCES warehouses(id) ON DELETE SET NULL,
    status               VARCHAR(20) NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending','assigned','packed','shipped','delivered','cancelled')),
    delivery_address     TEXT NOT NULL,
    preferred_date       DATE,
    subtotal             NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount_amount      NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_price          NUMERIC(12,2) NOT NULL DEFAULT 0,
    promotion_id         INTEGER,                         -- promo applied at order time
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_orders_customer  ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_warehouse ON orders(assigned_warehouse_id);
CREATE INDEX IF NOT EXISTS idx_orders_status    ON orders(status);

-- Order line items (one row per batch in an order) --------------------------
CREATE TABLE IF NOT EXISTS order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    batch_pk    INTEGER NOT NULL REFERENCES jaggery_batches(id) ON DELETE RESTRICT,
    qty_kg      NUMERIC(10,2) NOT NULL CHECK (qty_kg > 0),
    unit_price  NUMERIC(10,2) NOT NULL,
    line_total  NUMERIC(12,2) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_batch ON order_items(batch_pk);

-- Promotions ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS promotions (
    id               SERIAL PRIMARY KEY,
    title            VARCHAR(160) NOT NULL,
    discount_percent NUMERIC(5,2) NOT NULL CHECK (discount_percent BETWEEN 0 AND 100),
    min_qty          NUMERIC(10,2) NOT NULL DEFAULT 0,
    start_date       DATE NOT NULL,
    end_date         DATE NOT NULL,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_promo_dates CHECK (end_date >= start_date)
);
CREATE INDEX IF NOT EXISTS idx_promotions_active ON promotions(is_active, start_date, end_date);

-- FK for promotion applied to order (added after promotions table exists)
DO $$ BEGIN
    ALTER TABLE orders
        ADD CONSTRAINT fk_orders_promotion
        FOREIGN KEY (promotion_id) REFERENCES promotions(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
