-- v22: warehouse "delete stock" with an admin alert.
-- A warehouse can delete (soft-delete) a stock: it vanishes from the customer and
-- warehouse views immediately, but the admin gets an alarm and sees it highlighted.
-- Once the admin acknowledges it (delete_ack = TRUE) it disappears from the admin view too.
ALTER TABLE jaggery_batches ADD COLUMN IF NOT EXISTS deleted_at  TIMESTAMPTZ;
ALTER TABLE jaggery_batches ADD COLUMN IF NOT EXISTS delete_ack  BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_batches_deleted ON jaggery_batches (deleted_at) WHERE deleted_at IS NOT NULL;
