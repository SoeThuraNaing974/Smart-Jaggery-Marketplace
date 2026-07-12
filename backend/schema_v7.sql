-- ============================================================================
-- v7 migration — subscription payments (KPay / Wave Pay / AYA Pay / CB Pay / Bank).
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v7.sql
-- ============================================================================
CREATE TABLE IF NOT EXISTS payments (
    id              SERIAL PRIMARY KEY,
    warehouse_id    INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES warehouse_subscriptions(id) ON DELETE SET NULL,
    plan_id         INTEGER REFERENCES subscription_plans(id) ON DELETE SET NULL,
    amount          NUMERIC(10,2) NOT NULL,
    method          VARCHAR(20) NOT NULL
                    CHECK (method IN ('kpay','wavepay','ayapay','cbpay','yomapay','bank')),
    payer           VARCHAR(120),     -- payer phone / account name
    reference       VARCHAR(120),     -- transaction id / slip number
    status          VARCHAR(20) NOT NULL DEFAULT 'paid',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_payments_warehouse ON payments(warehouse_id, created_at);
