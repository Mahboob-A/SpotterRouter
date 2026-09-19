#!/usr/bin/env bash
set -euo pipefail

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting development backend server with reload on 0.0.0.0:8000..."
exec gunicorn fuel_router.wsgi:application \
    --bind 0.0.0.0:8000 \
    --reload \
    --access-logfile - \
    --error-logfile -
