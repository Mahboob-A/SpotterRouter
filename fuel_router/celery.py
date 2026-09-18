"""Celery application configured from Django settings."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_router.settings")

app = Celery("fuel_router")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
