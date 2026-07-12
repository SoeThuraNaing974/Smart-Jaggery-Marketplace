-- v18: emailed OTP to confirm a customer's online payment
ALTER TABLE users ADD COLUMN IF NOT EXISTS pay_otp_hash    VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS pay_otp_expires TIMESTAMPTZ;
