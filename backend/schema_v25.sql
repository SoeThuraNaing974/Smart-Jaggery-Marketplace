-- v25 migration — "Block" (suspend) accounts. A blocked user/warehouse keeps ALL
-- its data (unlike delete) but is locked out: they see a notice and can perform no
-- actions until the admin unblocks them. A warehouse block locks out its staff too.
ALTER TABLE users      ADD COLUMN IF NOT EXISTS blocked BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS blocked BOOLEAN NOT NULL DEFAULT false;
