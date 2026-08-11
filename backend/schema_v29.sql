-- ===========================================================================
-- v29 migration — Category names are free text (no uniqueness)
--
-- `jaggery_batches.batch_id` is the category NAME shown to people, not a
-- machine key. The old `UNIQUE (batch_id)` treated it as a key, which broke
-- ordinary editing:
--
--   * A SOFT-DELETED category kept reserving its name forever. The row is
--     invisible in every screen, yet renaming a live category to that name
--     failed with "category name already exists" — pointing at something the
--     admin could neither see nor remove.
--   * Two warehouses could not both stock a category with the same everyday
--     name (e.g. "ထန်းလျက်ခဲ").
--
-- Rows are identified by their primary key `id` everywhere in the app, so the
-- name carries no referential weight. The constraint is dropped; names may
-- repeat. Blank names are still rejected in the API.
--
-- Idempotent: safe to run more than once.
-- ===========================================================================

BEGIN;

-- the original table-level constraint (created by schema.sql)
ALTER TABLE jaggery_batches DROP CONSTRAINT IF EXISTS jaggery_batches_batch_id_key;

-- a partial unique index from an earlier revision of this migration, if present
DROP INDEX IF EXISTS uq_batches_name_live;

-- plain (non-unique) index: name lookups/sorting stay fast without constraining
CREATE INDEX IF NOT EXISTS idx_batches_name ON jaggery_batches (lower(batch_id));

COMMIT;
