-- ============================================================================
-- v4 migration — warehouse subscription plans + purchased subscriptions.
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v4.sql
-- ============================================================================

-- Plan catalogue (managed by admin) ----------------------------------------
CREATE TABLE IF NOT EXISTS subscription_plans (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(80) NOT NULL,
    duration_months INTEGER NOT NULL CHECK (duration_months > 0),
    price           NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A warehouse's purchased subscription -------------------------------------
CREATE TABLE IF NOT EXISTS warehouse_subscriptions (
    id           SERIAL PRIMARY KEY,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    plan_id      INTEGER REFERENCES subscription_plans(id) ON DELETE SET NULL,
    start_date   DATE NOT NULL,
    end_date     DATE NOT NULL,
    price_paid   NUMERIC(10,2) NOT NULL DEFAULT 0,
    status       VARCHAR(20) NOT NULL DEFAULT 'active'
                 CHECK (status IN ('active','cancelled')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_whsub_warehouse ON warehouse_subscriptions(warehouse_id, end_date);

-- Seed the four standard plans (only if the catalogue is empty) -------------
INSERT INTO subscription_plans (name, duration_months, price)
SELECT * FROM (VALUES
    ('1 Month',  1,  499.00),
    ('2 Months', 2,  899.00),
    ('6 Months', 6, 2499.00),
    ('1 Year',  12, 4499.00)
) AS v(name, duration_months, price)
WHERE NOT EXISTS (SELECT 1 FROM subscription_plans);
