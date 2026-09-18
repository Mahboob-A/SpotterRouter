from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex


class RawStationImport(models.Model):
    opis_id = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.CharField(max_length=20)
    retail_price = models.DecimalField(max_digits=6, decimal_places=3)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["opis_id", "id"]


class Station(models.Model):
    opis_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    retail_price = models.DecimalField(max_digits=6, decimal_places=3)
    location = models.PointField(srid=4326, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["opis_id"]
        indexes = [
            GistIndex(fields=["location"], name="station_location_gist"),
        ]
