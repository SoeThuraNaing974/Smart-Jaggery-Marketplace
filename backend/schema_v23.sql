-- v23: track when each user was last active (login / page activity) so the admin
-- directory can show whether a user is Active or Inactive.
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ;
