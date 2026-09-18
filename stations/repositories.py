from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from django.contrib.gis.db.models.functions import Distance, LineLocatePoint
from django.contrib.gis.geos import LineString, Point
from django.contrib.gis.measure import D
from django.db.models import QuerySet

from core.constants import CORRIDOR_BUFFER_MILES
from core.repositories import BaseRepository
from stations.models import Station


@dataclass(frozen=True)
class StationCandidate:
    station_id: int
    opis_id: str
    name: str
    city: str
    state: str
    location: Point
    retail_price: Decimal
    distance_from_start_miles: Decimal


class StationRepository(BaseRepository[Station]):
    model = Station

    def get_by_opis_id(self, opis_id: str) -> Station | None:
        return self.model.objects.filter(opis_id=opis_id).first()

    def needing_geocoding(self) -> QuerySet[Station]:
        return self.model.objects.filter(location__isnull=True).order_by("opis_id")

    def exists(self) -> bool:
        return self.model.objects.exists()

    def clear_all(self) -> int:
        deleted, _ = self.model.objects.all().delete()
        return deleted

    def bulk_create(
        self,
        stations: Sequence[Station],
        batch_size: int = 1000,
    ) -> list[Station]:
        return list(self.model.objects.bulk_create(stations, batch_size=batch_size))

    def bulk_update_locations(
        self,
        stations: Sequence[Station],
        batch_size: int = 1000,
    ) -> int:
        return self.model.objects.bulk_update(
            stations,
            fields=["location"],
            batch_size=batch_size,
        )

    def find_in_corridor(
        self,
        route_geometry: LineString,
        buffer_miles: float | Decimal = CORRIDOR_BUFFER_MILES,
        total_route_distance_miles: float | Decimal = Decimal("0"),
    ) -> list[StationCandidate]:
        """Find stations within buffer miles of route and project along route."""
        total_miles_float = float(total_route_distance_miles)
        buffer_mi_float = float(buffer_miles)

        queryset = (
            self.model.objects.exclude(location__isnull=True)
            .annotate(
                dist=Distance("location", route_geometry),
                fraction=LineLocatePoint(route_geometry, "location"),
            )
            .filter(dist__lte=D(mi=buffer_mi_float))
            .order_by("fraction")
        )

        candidates: list[StationCandidate] = []
        for station in queryset:
            if station.location is None:
                continue
            fraction_val = float(getattr(station, "fraction", 0.0) or 0.0)
            distance_miles = Decimal(
                str(round(fraction_val * total_miles_float, 2))
            )
            candidates.append(
                StationCandidate(
                    station_id=station.id,
                    opis_id=station.opis_id,
                    name=station.name,
                    city=station.city,
                    state=station.state,
                    location=station.location,
                    retail_price=station.retail_price,
                    distance_from_start_miles=distance_miles,
                )
            )
        return candidates
