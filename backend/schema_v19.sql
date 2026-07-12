-- v19: multiple images per product
--   * batch_images  : extra photos for a jaggery batch (the cover stays in jaggery_batches.image_path)
--   * product_requests.extra_images : comma-separated extra photo filenames added at request time,
--                                      copied into batch_images when the admin approves the request.

CREATE TABLE IF NOT EXISTS batch_images (
    id          SERIAL PRIMARY KEY,
    batch_id    INTEGER NOT NULL REFERENCES jaggery_batches(id) ON DELETE CASCADE,
    image_path  VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_batch_images_batch ON batch_images(batch_id);

ALTER TABLE product_requests ADD COLUMN IF NOT EXISTS extra_images TEXT;
