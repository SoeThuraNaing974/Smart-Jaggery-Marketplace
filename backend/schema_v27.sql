-- v27 migration — checkout delivery location (Local / Foreign).
-- The delivery "pincode" column now holds a location NAME (a Myanmar city when the
-- customer picks Local, a country when they pick Foreign) instead of a short code,
-- so VARCHAR(12) is too small ("United Arab Emirates", "Pyin Oo Lwin", ...).
ALTER TABLE users            ALTER COLUMN pincode TYPE VARCHAR(60);
ALTER TABLE orders           ALTER COLUMN pincode TYPE VARCHAR(60);
ALTER TABLE delivery_charges ALTER COLUMN pincode TYPE VARCHAR(60);

-- Which of the two checkout options the customer picked. Kept on the order so a
-- repeated order re-prices the same way (a foreign country with no row of its own
-- falls back to the admin's catch-all "Foreign" charge).
ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_scope VARCHAR(10) NOT NULL DEFAULT 'local';
