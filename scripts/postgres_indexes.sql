CREATE INDEX IF NOT EXISTS ix_expense_user_date
ON expense (user_id, date DESC);

CREATE INDEX IF NOT EXISTS ix_expense_user_category_date
ON expense (user_id, category, date DESC);

CREATE INDEX IF NOT EXISTS ix_income_user_date
ON income (user_id, date DESC);

CREATE INDEX IF NOT EXISTS ix_watchlist_user_added_date
ON watchlist (user_id, added_date DESC);

-- PostgreSQL already backs this unique constraint with a unique index.
-- Keep this only if the migrated schema is missing the original constraint/index.
CREATE UNIQUE INDEX IF NOT EXISTS ux_categorybudget_user_category
ON category_budget (user_id, category);

EXPLAIN ANALYZE
SELECT category, SUM(amount)
FROM expense
WHERE user_id = 123
GROUP BY category;
