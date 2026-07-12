-- v17: permanent per-customer order sequence number
ALTER TABLE users  ADD COLUMN IF NOT EXISTS order_count  INTEGER NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_seq INTEGER;

-- backfill existing orders: number each customer's orders by placement time
WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at, id) AS rn
  FROM orders
)
UPDATE orders o SET customer_seq = r.rn
FROM ranked r WHERE o.id = r.id AND o.customer_seq IS NULL;

-- set each user's monotonic counter to their highest assigned sequence
UPDATE users u
SET order_count = COALESCE((SELECT MAX(customer_seq) FROM orders o WHERE o.customer_id = u.id), 0);
