-- v26 migration — optional time limit on a block. When blocked_until is set, the
-- block auto-expires at that moment (access returns automatically). NULL = no limit
-- (stays blocked until the admin unblocks). Only meaningful while blocked = true.
ALTER TABLE users      ADD COLUMN IF NOT EXISTS blocked_until TIMESTAMPTZ;
ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS blocked_until TIMESTAMPTZ;
