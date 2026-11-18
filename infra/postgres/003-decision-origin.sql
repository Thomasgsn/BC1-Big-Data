ALTER TABLE analyst_decision ADD COLUMN IF NOT EXISTS origin TEXT NOT NULL DEFAULT 'user_review'
  CHECK (origin IN ('user_review', 'automated_test'));
