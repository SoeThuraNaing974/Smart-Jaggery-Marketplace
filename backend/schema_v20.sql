-- v20: payment-driven order flow  ->  pending -> waiting -> shipped (+ cancelled)
--   pending  = order placed, payment NOT finished   (customer + admin only)
--   waiting  = payment finished / COD confirmed      (customer + warehouse + admin)
--   shipped  = warehouse shipped to the customer      (customer + warehouse + admin)

-- drop the old CHECK first so we can migrate into the new states
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_status_check;

-- migrate existing rows off the old states (assigned/packed/delivered)
UPDATE orders SET status = 'waiting'
  WHERE status IN ('assigned', 'packed') AND (payment_status = 'paid' OR payment_method = 'cod');
UPDATE orders SET status = 'pending'
  WHERE status IN ('assigned', 'packed');           -- remaining (unpaid, online) -> pending
UPDATE orders SET status = 'shipped' WHERE status = 'delivered';

-- add the new CHECK
ALTER TABLE orders ADD CONSTRAINT orders_status_check
  CHECK (status IN ('pending', 'waiting', 'shipped', 'cancelled'));
