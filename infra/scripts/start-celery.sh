#!/usr/bin/env bash
set -euo pipefail

echo "Starting Celery worker..."
exec celery -A fuel_router worker \
    --loglevel="${CELERY_LOG_LEVEL:-info}" \
    --concurrency="${CELERY_CONCURRENCY:-2}"
