import uuid
from decimal import Decimal

from django.contrib.gis.db import models

from core.constants import MAX_RANGE_MILES, MPG_CONSTANT


class TripPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    start_input = models.TextField()
    end_input = models.TextField()
    start_point = models.PointField(srid=4326)
    end_point = models.PointField(srid=4326)
    route_geometry = models.LineStringField(srid=4326)
    total_distance_miles = models.DecimalField(max_digits=8, decimal_places=2)
    total_gallons = models.DecimalField(max_digits=8, decimal_places=3)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    cache_key = models.CharField(max_length=64, unique=True, db_index=True)
    pricing_dataset = models.ForeignKey(
        "stations.PricingDataset",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="trip_plans",
    )
    ai_explanation = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_requested_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-last_requested_at", "-created_at"]

    @property
    def total_gallons_purchased(self) -> Decimal:
        """Sum of gallons purchased across planned en-route refueling stops."""
        prefetched = getattr(self, "_prefetched_objects_cache", {})
        if "fuel_stops" in prefetched:
            stops = prefetched["fuel_stops"]
        else:
            stops = list(self.fuel_stops.all())
        if not stops:
            return Decimal("0.000")
        return sum((stop.gallons_purchased for stop in stops), Decimal("0.000"))

    @property
    def initial_fuel_gallons(self) -> Decimal:
        """Vehicle tank capacity pre-loaded at origin (500-mi range at 10 MPG)."""
        return Decimal(str(MAX_RANGE_MILES)) / MPG_CONSTANT

    @property
    def is_cache_hit(self) -> bool:
        """Indicate whether this instance was resolved from cache during planning."""
        return getattr(self, "_is_cache_hit", False)

    @is_cache_hit.setter
    def is_cache_hit(self, value: bool) -> None:
        self._is_cache_hit = bool(value)


class FuelStop(models.Model):
    id = models.BigAutoField(primary_key=True)
    trip_plan = models.ForeignKey(
        TripPlan,
        on_delete=models.CASCADE,
        related_name="fuel_stops",
    )
    station = models.ForeignKey(
        "stations.Station",
        on_delete=models.PROTECT,
        related_name="fuel_stops",
    )
    stop_order = models.PositiveSmallIntegerField()
    distance_from_start_miles = models.DecimalField(max_digits=8, decimal_places=2)
    gallons_purchased = models.DecimalField(max_digits=8, decimal_places=3)
    price_per_gallon = models.DecimalField(max_digits=6, decimal_places=3)
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["stop_order"]
        unique_together = [("trip_plan", "stop_order")]
