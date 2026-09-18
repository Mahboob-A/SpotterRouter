import uuid

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("stations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TripPlan",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("start_input", models.TextField()),
                ("end_input", models.TextField()),
                (
                    "start_point",
                    django.contrib.gis.db.models.fields.PointField(srid=4326),
                ),
                (
                    "end_point",
                    django.contrib.gis.db.models.fields.PointField(srid=4326),
                ),
                (
                    "route_geometry",
                    django.contrib.gis.db.models.fields.LineStringField(srid=4326),
                ),
                (
                    "total_distance_miles",
                    models.DecimalField(decimal_places=2, max_digits=8),
                ),
                (
                    "total_gallons",
                    models.DecimalField(decimal_places=3, max_digits=8),
                ),
                (
                    "total_cost",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                (
                    "cache_key",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                ("ai_explanation", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="FuelStop",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("stop_order", models.PositiveSmallIntegerField()),
                (
                    "distance_from_start_miles",
                    models.DecimalField(decimal_places=2, max_digits=8),
                ),
                (
                    "gallons_purchased",
                    models.DecimalField(decimal_places=3, max_digits=8),
                ),
                (
                    "price_per_gallon",
                    models.DecimalField(decimal_places=3, max_digits=6),
                ),
                (
                    "cost",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                (
                    "station",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="fuel_stops",
                        to="stations.station",
                    ),
                ),
                (
                    "trip_plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fuel_stops",
                        to="trips.tripplan",
                    ),
                ),
            ],
            options={
                "ordering": ["stop_order"],
                "unique_together": {("trip_plan", "stop_order")},
            },
        ),
    ]
