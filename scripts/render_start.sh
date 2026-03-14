#!/usr/bin/env bash
# Render start command for the Expense Tracker App.
# Usage: set this script as the Start Command in Render dashboard, or keep Procfile pointing here.
#
# Environment variables:
#   DATABASE_URL      (required) PostgreSQL connection string
#   RUN_MIGRATIONS    (optional) set to 1/true/yes/on to run `flask db upgrade` before starting
#   AUTO_CREATE_TABLES (optional) set to 1/true/yes/on to create tables via db.create_all() on startup

set -e

# ── 1. Resolve and validate database URL ────────────────────────────────────
RAW_DB_URL="${DATABASE_URL:-${NEON_DATABASE_URL:-${POSTGRES_URL:-${VALUE:-${Value:-}}}}}"

if [ -z "$RAW_DB_URL" ]; then
    echo "ERROR: DATABASE_URL is not set."
    echo "Set it to your Neon / PostgreSQL connection string in the Render environment variables."
    echo "Example: postgresql://user:password@host/dbname?sslmode=require"
    exit 1
fi

# Recover from accidental UI entry like: "Value =postgresql://..."
DB_URL="${RAW_DB_URL#*=}"

case "$DB_URL" in
    *postgresql://*)
        DB_URL="postgresql://${DB_URL#*postgresql://}"
        ;;
    *postgres://*)
        DB_URL="postgres://${DB_URL#*postgres://}"
        ;;
    *mysql://*|*mysql+pymysql://*)
        echo "ERROR: MySQL URL detected in env vars, but this app expects Neon/PostgreSQL."
        echo "Fix DATABASE_URL to your Neon Postgres connection string."
        exit 1
        ;;
esac

export DATABASE_URL="$DB_URL"

# ── 2. Optionally run Flask-Migrate migrations ───────────────────────────────
# Tell the Flask CLI which application to load.
export FLASK_APP="${FLASK_APP:-wsgi}"

case "${RUN_MIGRATIONS:-0}" in
    1|true|yes|on)
        echo "RUN_MIGRATIONS is enabled – running: flask db upgrade"
        flask db upgrade
        echo "Migrations complete."
        ;;
    *)
        echo "RUN_MIGRATIONS is not enabled; skipping flask db upgrade."
        echo "Set RUN_MIGRATIONS=1 to run migrations automatically on startup."
        ;;
esac

# ── 3. Start gunicorn ────────────────────────────────────────────────────────
echo "Starting gunicorn..."
exec gunicorn wsgi:app \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}"
