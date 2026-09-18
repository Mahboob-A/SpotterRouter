import uuid
from decimal import Decimal

from django.contrib.gis.geos import LineString, Point
import pytest

from stations.models import Station
from trips.models import FuelStop, TripPlan
from trips.repositories import FuelStopRepository, TripPlanRepository


def _make_station(opis_id: str, name: str, lat: float, lon: float) -> Station:
    return Station.objects.create(
        opis_id=opis_id,
        name=name,
        address="123 Main St",
        city="Testville",
        state="TX",
        rack_price=Decimal("3.500"),
        retail_price=Decimal("3.850"),
        location=Point(lon, lat, srid=4326),
    )


def _make_trip_plan(cache_key: str = "cache-key-default") -> TripPlan:
    start_pt = Point(-87.6298, 41.8781, srid=4326)
    end_pt = Point(-96.7970, 32.7767, srid=4326)
    route_geom = LineString([start_pt, end_pt], srid=4326)
    return TripPlan(
        start_input="Chicago, IL",
        end_input="Dallas, TX",
        start_point=start_pt,
        end_point=end_pt,
        route_geometry=route_geom,
        total_distance_miles=Decimal("967.30"),
        total_gallons=Decimal("96.730"),
        total_cost=Decimal("341.52"),
        cache_key=cache_key,
    )


@pytest.mark.django_db
class TestTripPlanRepository:
    def test_save_and_get_by_id(self) -> None:
        repo = TripPlanRepository()
        trip = _make_trip_plan("cache-1")
        saved = repo.save(trip)

        assert saved.id is not None
        fetched = repo.get_by_id(saved.id)
        assert fetched is not None
        assert fetched.id == saved.id
        assert fetched.cache_key == "cache-1"

    def test_get_by_id_returns_none_for_missing(self) -> None:
        repo = TripPlanRepository()
        assert repo.get_by_id(uuid.uuid4()) is None

    def test_get_by_cache_key_with_prefetched_stops(
        self, django_assert_num_queries: pytest.FixtureRequest
    ) -> None:
        repo = TripPlanRepository()
        trip = _make_trip_plan("cache-lookup-key")
        repo.save(trip)

        station = _make_station("ST-01", "Stop 1", 35.0, -90.0)
        FuelStop.objects.create(
            trip_plan=trip,
            station=station,
            stop_order=1,
            distance_from_start_miles=Decimal("450.00"),
            gallons_purchased=Decimal("45.000"),
            price_per_gallon=Decimal("3.850"),
            cost=Decimal("173.25"),
        )

        fetched = repo.get_by_cache_key("cache-lookup-key")
        assert fetched is not None
        assert fetched.id == trip.id

        # Accessing prefetched fuel stops and station should not trigger extra queries
        stops = list(fetched.fuel_stops.all())
        assert len(stops) == 1
        assert stops[0].station.name == "Stop 1"

    def test_get_by_cache_key_returns_none_for_missing(self) -> None:
        repo = TripPlanRepository()
        assert repo.get_by_cache_key("non-existent-key") is None

    def test_update_explanation(self) -> None:
        repo = TripPlanRepository()
        trip = _make_trip_plan("cache-expl")
        repo.save(trip)

        assert trip.ai_explanation is None
        success = repo.update_explanation(
            trip.id, "Recommended route due to low fuel prices."
        )
        assert success is True

        refetched = repo.get_by_id(trip.id)
        assert refetched is not None
        assert (
            refetched.ai_explanation
            == "Recommended route due to low fuel prices."
        )

    def test_update_explanation_missing_trip_returns_false(self) -> None:
        repo = TripPlanRepository()
        assert repo.update_explanation(uuid.uuid4(), "No trip") is False

    def test_list_recent(self) -> None:
        repo = TripPlanRepository()
        for idx in range(5):
            trip = _make_trip_plan(f"cache-recent-{idx}")
            repo.save(trip)

        recent = repo.list_recent(limit=3)
        assert len(recent) == 3
        # Should be ordered newest first
        assert recent[0].created_at >= recent[1].created_at
        assert recent[1].created_at >= recent[2].created_at


@pytest.mark.django_db
class TestFuelStopRepository:
    def test_save_single_fuel_stop(self) -> None:
        trip_repo = TripPlanRepository()
        trip = _make_trip_plan("cache-stop-save")
        trip_repo.save(trip)

        station = _make_station("ST-02", "Stop 2", 36.0, -91.0)
        stop_repo = FuelStopRepository()

        stop = FuelStop(
            trip_plan=trip,
            station=station,
            stop_order=1,
            distance_from_start_miles=Decimal("400.00"),
            gallons_purchased=Decimal("40.000"),
            price_per_gallon=Decimal("3.850"),
            cost=Decimal("154.00"),
        )
        saved_stop = stop_repo.save(stop)
        assert saved_stop.id is not None

        fetched = stop_repo.get_by_id(saved_stop.id)
        assert fetched is not None
        assert fetched.trip_plan_id == trip.id
        assert fetched.stop_order == 1

    def test_save_many_and_get_for_trip(self) -> None:
        trip_repo = TripPlanRepository()
        trip = _make_trip_plan("cache-stop-many")
        trip_repo.save(trip)

        station_1 = _make_station("ST-03", "Stop A", 36.0, -91.0)
        station_2 = _make_station("ST-04", "Stop B", 37.0, -92.0)

        stop_repo = FuelStopRepository()
        stops = [
            FuelStop(
                trip_plan=trip,
                station=station_1,
                stop_order=1,
                distance_from_start_miles=Decimal("350.00"),
                gallons_purchased=Decimal("35.000"),
                price_per_gallon=Decimal("3.700"),
                cost=Decimal("129.50"),
            ),
            FuelStop(
                trip_plan=trip,
                station=station_2,
                stop_order=2,
                distance_from_start_miles=Decimal("750.00"),
                gallons_purchased=Decimal("40.000"),
                price_per_gallon=Decimal("3.650"),
                cost=Decimal("146.00"),
            ),
        ]
        created = stop_repo.save_many(stops)
        assert len(created) == 2

        fetched_stops = stop_repo.get_for_trip(trip.id)
        assert len(fetched_stops) == 2
        assert fetched_stops[0].stop_order == 1
        assert fetched_stops[0].station.name == "Stop A"
        assert fetched_stops[1].stop_order == 2
        assert fetched_stops[1].station.name == "Stop B"

    def test_get_by_id_returns_none_for_missing(self) -> None:
        stop_repo = FuelStopRepository()
        assert stop_repo.get_by_id(999999) is None
