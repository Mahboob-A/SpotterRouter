#!/usr/bin/env bash
set -euo pipefail

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static assets into static volume..."
python manage.py collectstatic --noinput

if [ "${AUTO_LOAD_STATIONS:-False}" = "True" ]; then
    echo "Checking station database status..."
    STATION_COUNT=$(python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuel_router.settings')
django.setup()
from stations.models import Station
print(Station.objects.count())
" 2>/dev/null || echo "0")

    if [ "$STATION_COUNT" -eq "0" ]; then
        echo "No stations detected. Performing initial data import, load, and geocoding..."
        python manage.py import_stations dataset/fuel-prices-for-be-assessment.csv || true
        python manage.py load_stations || true
        python manage.py geocode_stations || true
        echo "Initial station data loading complete."
    else
        echo "Station dataset already loaded ($STATION_COUNT stations present)."
    fi
fi

echo "Starting production backend server on 0.0.0.0:8000..."
exec gunicorn fuel_router.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-4}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --worker-class gthread \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
