-- ============================================================================
-- v6 migration — warehouse product (batch) upload requests, approved by admin.
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v6.sql
-- ============================================================================
CREATE TABLE IF NOT EXISTS product_requests (
    id            SERIAL PRIMARY KEY,
    warehouse_id  INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    requested_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    batch_code    VARCHAR(60) NOT NULL,
    grade         VARCHAR(1) NOT NULL CHECK (grade IN ('A','B','C')),
    qty_kg        NUMERIC(10,2) NOT NULL CHECK (qty_kg >= 0),
    harvest_date  DATE NOT NULL,
    price_per_kg  NUMERIC(10,2) NOT NULL CHECK (price_per_kg >= 0),
    status        VARCHAR(20) NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','approved','rejected')),
    admin_note    TEXT,
    reviewed_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_batch_id INTEGER REFERENCES jaggery_batches(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_prodreq_status ON product_requests(status);
CREATE INDEX IF NOT EXISTS idx_prodreq_warehouse ON product_requests(warehouse_id, created_at);
