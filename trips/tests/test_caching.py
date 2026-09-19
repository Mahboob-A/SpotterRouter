import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import redis
from django.contrib.gis.geos import LineString, Point

from stations.models import Station
from trips.caching import TripCacheManager, build_trip_cache_key
from trips.models import FuelStop, TripPlan
from trips.repositories import TripPlanRepository


def test_build_trip_cache_key_normalizes_casing_and_whitespace() -> None:
    key1 = build_trip_cache_key(" Chicago,   IL ", "Dallas,   TX")
    key2 = build_trip_cache_key("chicago, il", "dallas, tx")
    key3 = build_trip_cache_key("  CHICAGO,   IL  ", "  DALLAS, TX  ")
    key_diff = build_trip_cache_key("Austin, TX", "Dallas, TX")

    assert key1 == key2 == key3
    assert len(key1) == 64
    assert key1 != key_diff


def test_cache_manager_redis_hit_returns_plan_without_db_query() -> None:
    plan_id = uuid.uuid4()
    cache_key = "a" * 64
    mock_redis = MagicMock()
    mock_redis.get.return_value = (
        '{"id": "' + str(plan_id) + '", "start_input": "Chicago, IL", '
        '"end_input": "Dallas, TX", "start_point": [-87.6298, 41.8781], '
        '"end_point": [-96.7970, 32.7767], '
        '"route_geometry": {"type": "LineString", "coordinates": '
        '[[-87.6298, 41.8781], [-96.7970, 32.7767]]}, '
        '"total_distance_miles": "967.30", "total_gallons": "96.730", '
        '"total_cost": "341.52", "cache_key": "' + cache_key + '", '
        '"ai_explanation": null, "created_at": "2026-09-18T12:00:00Z", '
        '"fuel_stops": [{"stop_order": 1, "station_id": 10, '
        '"station_opis_id": "OPIS_10", "station_name": "Test Station", '
        '"station_city": "City", "station_state": "IL", '
        '"distance_from_start_miles": "400.00", "gallons_purchased": "40.000", '
        '"price_per_gallon": "3.500", "cost": "140.00"}]}'
    )
    mock_repo = MagicMock(spec=TripPlanRepository)

    manager = TripCacheManager(redis_client=mock_redis, repository=mock_repo)
    result = manager.get(cache_key)

    assert result is not None
    assert result.id == plan_id
    assert result.total_distance_miles == Decimal("967.30")
    mock_redis.get.assert_called_once_with(f"trip:{cache_key}")
    mock_repo.get_by_cache_key.assert_not_called()

    stops = list(result.fuel_stops.all())
    assert len(stops) == 1
    assert stops[0].stop_order == 1
    assert stops[0].station.name == "Test Station"
    assert stops[0].cost == Decimal("140.00")


@pytest.mark.django_db
def test_cache_manager_redis_miss_queries_postgres_and_repopulates_redis() -> None:
    cache_key = "b" * 64
    plan = TripPlan(
        id=uuid.uuid4(),
        start_input="Chicago, IL",
        end_input="Dallas, TX",
        start_point=Point(-87.6298, 41.8781, srid=4326),
        end_point=Point(-96.7970, 32.7767, srid=4326),
        route_geometry=LineString(
            [(-87.6298, 41.8781), (-96.7970, 32.7767)],
            srid=4326,
        ),
        total_distance_miles=Decimal("967.30"),
        total_gallons=Decimal("96.730"),
        total_cost=Decimal("341.52"),
        cache_key=cache_key,
    )
    station = Station(
        id=99,
        opis_id="OPIS_99",
        name="Postgres Station",
        city="Some City",
        state="MO",
        retail_price=Decimal("3.250"),
    )
    stop = FuelStop(
        trip_plan=plan,
        station=station,
        stop_order=1,
        distance_from_start_miles=Decimal("450.00"),
        gallons_purchased=Decimal("45.000"),
        price_per_gallon=Decimal("3.250"),
        cost=Decimal("146.25"),
    )
    plan._prefetched_objects_cache = {  # type: ignore[attr-defined]
        "fuel_stops": [stop],
    }

    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_repo = MagicMock(spec=TripPlanRepository)
    mock_repo.get_by_cache_key.return_value = plan

    manager = TripCacheManager(redis_client=mock_redis, repository=mock_repo)
    result = manager.get(cache_key)

    assert result == plan
    mock_repo.get_by_cache_key.assert_called_once_with(cache_key)
    mock_redis.set.assert_called_once()
    set_args, set_kwargs = mock_redis.set.call_args
    assert set_args[0] == f"trip:{cache_key}"
    assert set_kwargs.get("ex") == 86400


def test_cache_manager_graceful_degradation_on_redis_error() -> None:
    cache_key = "c" * 64
    mock_redis = MagicMock()
    mock_redis.get.side_effect = redis.ConnectionError("Connection refused")
    mock_redis.set.side_effect = redis.ConnectionError("Connection refused")

    plan = TripPlan(
        id=uuid.uuid4(),
        start_input="A",
        end_input="B",
        start_point=Point(0, 0, srid=4326),
        end_point=Point(1, 1, srid=4326),
        route_geometry=LineString([(0, 0), (1, 1)], srid=4326),
        total_distance_miles=Decimal("10.00"),
        total_gallons=Decimal("1.000"),
        total_cost=Decimal("3.00"),
        cache_key=cache_key,
    )
    plan._prefetched_objects_cache = {  # type: ignore[attr-defined]
        "fuel_stops": [],
    }

    mock_repo = MagicMock(spec=TripPlanRepository)
    mock_repo.get_by_cache_key.return_value = plan

    manager = TripCacheManager(redis_client=mock_redis, repository=mock_repo)

    # get should not raise and should fallback to Postgres
    result = manager.get(cache_key)
    assert result == plan

    # set should not raise on redis connection error
    manager.set(plan)
