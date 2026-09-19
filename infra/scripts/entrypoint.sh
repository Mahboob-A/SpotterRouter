#!/usr/bin/env bash
set -euo pipefail

# Wait for PostgreSQL if DATABASE_URL is defined
if [ -n "${DATABASE_URL:-}" ]; then
    echo "Waiting for database connection..."
    python -c "
import os, sys, time
import psycopg

url = os.environ.get('DATABASE_URL', '')
if url.startswith('postgis://'):
    url = 'postgresql://' + url[len('postgis://'):]

for attempt in range(1, 31):
    try:
        conn = psycopg.connect(url, connect_timeout=2)
        conn.close()
        sys.exit(0)
    except Exception:
        time.sleep(1)
sys.exit(1)
" || { echo "Database connection failed after 30 attempts."; exit 1; }
    echo "Database is ready."
fi

exec "$@"
