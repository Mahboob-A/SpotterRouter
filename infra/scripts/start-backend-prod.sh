#!/usr/bin/env bash
set -euo pipefail

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting production backend server on 0.0.0.0:8000..."
exec gunicorn fuel_router.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-4}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --worker-class gthread \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
