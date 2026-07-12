-- v16: phone number captured on the order payment form
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_phone VARCHAR(30);
