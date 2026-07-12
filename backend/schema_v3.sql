-- ============================================================================
-- v3 migration — per-order messaging between customers and warehouse staff.
-- Apply:  psql -U postgres -p 5433 -d jaggery_db -f schema_v3.sql
-- ============================================================================
CREATE TABLE IF NOT EXISTS order_messages (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    sender_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    sender_role VARCHAR(20) NOT NULL,
    message     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_order_messages_order ON order_messages(order_id, created_at);
