-- v15: customer order payments + delivery/pickup fulfillment
ALTER TABLE orders ADD COLUMN IF NOT EXISTS fulfillment       VARCHAR(10)  NOT NULL DEFAULT 'delivery';
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method    VARCHAR(20);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_status    VARCHAR(20)  NOT NULL DEFAULT 'unpaid';
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_reference VARCHAR(120);

-- guard the small value sets (VARCHAR + CHECK, matching the project's convention)
DO $$ BEGIN
  ALTER TABLE orders ADD CONSTRAINT orders_fulfillment_chk   CHECK (fulfillment IN ('delivery','pickup'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  ALTER TABLE orders ADD CONSTRAINT orders_paystatus_chk     CHECK (payment_status IN ('unpaid','paid'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
