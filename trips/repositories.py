import uuid
from collections.abc import Sequence

from core.repositories import BaseRepository
from trips.models import FuelStop, TripPlan


class TripPlanRepository(BaseRepository[TripPlan]):
    """Data access repository for trip plan records."""

    model = TripPlan

    def save(self, trip_plan: TripPlan) -> TripPlan:
        trip_plan.save()
        return trip_plan

    def get_by_id(self, object_id: object) -> TripPlan | None:
        if not isinstance(object_id, (uuid.UUID, str)):
            return None
        return (
            self.model.objects.filter(pk=object_id)
            .select_related("pricing_dataset")
            .prefetch_related("fuel_stops__station")
            .first()
        )

    def get_by_cache_key(self, cache_key: str) -> TripPlan | None:
        return (
            self.model.objects.filter(cache_key=cache_key)
            .select_related("pricing_dataset")
            .prefetch_related("fuel_stops__station")
            .first()
        )

    def update_explanation(
        self,
        trip_id: uuid.UUID,
        explanation: str,
    ) -> bool:
        updated = self.model.objects.filter(pk=trip_id).update(
            ai_explanation=explanation
        )
        return updated > 0

    def touch_recency(self, trip_id: uuid.UUID) -> bool:
        from django.utils import timezone

        updated = self.model.objects.filter(pk=trip_id).update(
            last_requested_at=timezone.now()
        )
        return updated > 0

    def list_recent(self, limit: int = 20, offset: int = 0) -> list[TripPlan]:
        from django.db.models.functions import Coalesce

        return list(
            self.model.objects.all()
            .order_by(
                Coalesce("last_requested_at", "created_at").desc(),
                "-created_at",
            )
            .select_related("pricing_dataset")
            .prefetch_related("fuel_stops__station")[offset : offset + limit]
        )

    def count_total(self) -> int:
        return self.model.objects.count()


class FuelStopRepository(BaseRepository[FuelStop]):
    """Data access repository for trip fuel stop records."""

    model = FuelStop

    def save(self, stop: FuelStop) -> FuelStop:
        stop.save()
        return stop

    def save_many(self, stops: Sequence[FuelStop]) -> list[FuelStop]:
        return list(self.model.objects.bulk_create(stops))

    def get_for_trip(self, trip_plan_id: uuid.UUID) -> list[FuelStop]:
        return list(
            self.model.objects.filter(trip_plan_id=trip_plan_id)
            .select_related("station")
            .order_by("stop_order")
        )
