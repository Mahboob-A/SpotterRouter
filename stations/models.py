import uuid

from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex


class PricingDataset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version_code = models.CharField(max_length=64, unique=True, db_index=True)
    filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, db_index=True)
    station_count = models.PositiveIntegerField(default=0)
    min_price = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    max_price = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"PricingDataset({self.version_code}, active={self.is_active})"


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


class StationPrice(models.Model):
    dataset = models.ForeignKey(
        PricingDataset,
        on_delete=models.CASCADE,
        related_name="station_prices",
    )
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    retail_price = models.DecimalField(max_digits=6, decimal_places=3)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("dataset", "station")]
        indexes = [
            models.Index(fields=["dataset", "station"]),
        ]

