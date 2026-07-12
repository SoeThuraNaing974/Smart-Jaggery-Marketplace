-- v21: daily advertisements (admin-managed, shown on the customer side).
-- Icon-driven cards with an accent theme, optional call-to-action link, and an
-- optional scheduled date window (starts_on / ends_on) so an ad can run "daily"
-- for a chosen period. Date columns are used (not TIMESTAMPTZ) to keep the
-- "show today?" check simple and timezone-proof.
CREATE TABLE IF NOT EXISTS advertisements (
    id                  SERIAL PRIMARY KEY,
    title               VARCHAR(160) NOT NULL,
    body                TEXT,
    icon                VARCHAR(16)  NOT NULL DEFAULT '📣',
    accent              VARCHAR(20)  NOT NULL DEFAULT 'amber',
    link_url            VARCHAR(500),
    link_label          VARCHAR(80),
    is_active           BOOLEAN      NOT NULL DEFAULT TRUE,
    starts_on           DATE,
    ends_on             DATE,
    created_by_admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ads_active ON advertisements (is_active);
