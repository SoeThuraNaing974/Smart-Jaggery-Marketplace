-- v14: profile picture for users
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_path VARCHAR(255);
