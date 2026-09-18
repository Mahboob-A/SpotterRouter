from decimal import Decimal

import pytest
from django.contrib.gis.geos import LineString, Point

from stations.models import Station
from stations.repositories import StationCandidate, StationRepository


def _create_station(
    opis_id: str,
    name: str,
    location: Point | None,
    price: Decimal = Decimal("3.500"),
) -> Station:
    return Station.objects.create(
        opis_id=opis_id,
        name=name,
        city="Testville",
        state="TX",
        retail_price=price,
        location=location,
    )


@pytest.mark.django_db
class TestCorridorMatching:
    def test_stations_within_corridor_included_and_outside_excluded(
        self,
    ) -> None:
        route = LineString([Point(0.0, 0.0), Point(10.0, 0.0)], srid=4326)
        # Near: ~3.45 miles from route
        near_station = _create_station(
            opis_id="ST-NEAR",
            name="Near Route Station",
            location=Point(5.0, 0.05, srid=4326),
            price=Decimal("3.200"),
        )
        # Far: ~34.5 miles from route
        _create_station(
            opis_id="ST-FAR",
            name="Far Off Route Station",
            location=Point(5.0, 0.50, srid=4326),
            price=Decimal("2.900"),
        )

        repo = StationRepository()
        candidates = repo.find_in_corridor(
            route_geometry=route,
            buffer_miles=15.0,
            total_route_distance_miles=Decimal("1000.00"),
        )

        opis_ids = [c.opis_id for c in candidates]
        assert "ST-NEAR" in opis_ids
        assert "ST-FAR" not in opis_ids
        assert len(candidates) == 1

        candidate = candidates[0]
        assert isinstance(candidate, StationCandidate)
        assert candidate.station_id == near_station.id
        assert candidate.name == "Near Route Station"
        assert candidate.city == "Testville"
        assert candidate.state == "TX"
        assert candidate.retail_price == Decimal("3.200")
        assert candidate.distance_from_start_miles == Decimal("500.00")

    def test_stations_without_location_are_excluded(self) -> None:
        route = LineString([Point(0.0, 0.0), Point(10.0, 0.0)], srid=4326)
        _create_station(
            opis_id="ST-UNMAPPED",
            name="Unmapped Station",
            location=None,
        )

        repo = StationRepository()
        candidates = repo.find_in_corridor(
            route_geometry=route,
            buffer_miles=15.0,
            total_route_distance_miles=Decimal("500.00"),
        )
        assert [c.opis_id for c in candidates if c.opis_id == "ST-UNMAPPED"] == []

    def test_stations_ordered_by_projection_along_route(self) -> None:
        route = LineString([Point(0.0, 0.0), Point(10.0, 0.0)], srid=4326)

        # Create out of order along route
        _create_station(
            opis_id="ST-LATE",
            name="Mile 800 Stop",
            location=Point(8.0, 0.02, srid=4326),
        )
        _create_station(
            opis_id="ST-EARLY",
            name="Mile 200 Stop",
            location=Point(2.0, 0.02, srid=4326),
        )
        _create_station(
            opis_id="ST-MID",
            name="Mile 500 Stop",
            location=Point(5.0, 0.02, srid=4326),
        )

        repo = StationRepository()
        candidates = repo.find_in_corridor(
            route_geometry=route,
            buffer_miles=15.0,
            total_route_distance_miles=Decimal("1000.00"),
        )

        matched = [c for c in candidates if c.opis_id.startswith("ST-")]
        assert len(matched) == 3
        assert matched[0].opis_id == "ST-EARLY"
        assert matched[0].distance_from_start_miles == Decimal("200.00")
        assert matched[1].opis_id == "ST-MID"
        assert matched[1].distance_from_start_miles == Decimal("500.00")
        assert matched[2].opis_id == "ST-LATE"
        assert matched[2].distance_from_start_miles == Decimal("800.00")

    def test_empty_corridor_returns_empty_list(self) -> None:
        # Remote route in middle of the ocean
        remote_route = LineString(
            [Point(-140.0, 10.0), Point(-145.0, 10.0)],
            srid=4326,
        )
        repo = StationRepository()
        candidates = repo.find_in_corridor(
            route_geometry=remote_route,
            buffer_miles=15.0,
            total_route_distance_miles=Decimal("400.00"),
        )
        assert candidates == []
