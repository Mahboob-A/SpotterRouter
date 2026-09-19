from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.contrib.gis.geos import LineString, Point

from core.exceptions import (
    GeocodingUnresolvedError,
    InsufficientStationCoverageError,
    RoutingUnavailableError,
)
from routing.adapters.base import RouteResult
from routing.coordinates import Coordinates
from routing.services import GeocodingService, RoutingService
from stations.models import Station
from stations.repositories import (
    PricingDatasetRepository,
    StationCandidate,
    StationRepository,
)
from trips.caching import TripCacheManager
from trips.models import FuelStop, TripPlan
from trips.repositories import FuelStopRepository, TripPlanRepository
from trips.services import (
    OptimizationResult,
    RefuelOptimizationService,
    TripPlanningService,
)
from trips.strategies import FuelStopPlan


def test_plan_trip_cache_hit_bypasses_all_services() -> None:
    cached_plan = TripPlan(
        start_input="Chicago, IL",
        end_input="Dallas, TX",
        start_point=Point(-87.6298, 41.8781, srid=4326),
        end_point=Point(-96.7970, 32.7767, srid=4326),
        route_geometry=LineString(
            [(-87.6298, 41.8781), (-96.7970, 32.7767)],
            srid=4326,
        ),
        total_distance_miles=Decimal("950.00"),
        total_gallons=Decimal("95.000"),
        total_cost=Decimal("300.00"),
        cache_key="f" * 64,
    )
    mock_cache = MagicMock(spec=TripCacheManager)
    mock_cache.get.return_value = cached_plan

    mock_geocoding = MagicMock(spec=GeocodingService)
    mock_routing = MagicMock(spec=RoutingService)
    mock_stations = MagicMock(spec=StationRepository)
    mock_refuel = MagicMock(spec=RefuelOptimizationService)
    mock_datasets = MagicMock(spec=PricingDatasetRepository)
    mock_datasets.get_active.return_value = None

    service = TripPlanningService(
        geocoding_service=mock_geocoding,
        routing_service=mock_routing,
        station_repository=mock_stations,
        refuel_service=mock_refuel,
        cache_manager=mock_cache,
        dataset_repository=mock_datasets,
    )

    result = service.plan_trip("Chicago, IL", "Dallas, TX")

    assert result == cached_plan
    mock_geocoding.resolve.assert_not_called()
    mock_routing.get_route.assert_not_called()
    mock_stations.find_in_corridor.assert_not_called()
    mock_refuel.optimize.assert_not_called()


@pytest.mark.django_db
def test_plan_trip_full_orchestration_and_atomic_persistence() -> None:
    station = Station.objects.create(
        opis_id="OPIS_100",
        name="TA Test",
        city="Mount Vernon",
        state="IL",
        retail_price=Decimal("3.100"),
        location=Point(-88.90, 38.31, srid=4326),
    )

    start_coords = Coordinates(longitude=-87.6298, latitude=41.8781)
    end_coords = Coordinates(longitude=-96.7970, latitude=32.7767)

    mock_geocoding = MagicMock(spec=GeocodingService)
    mock_geocoding.resolve.side_effect = [start_coords, end_coords]

    route_geom = LineString(
        [(-87.6298, 41.8781), (-96.7970, 32.7767)],
        srid=4326,
    )
    route_result = RouteResult(
        route_geometry=route_geom,
        total_distance_miles=Decimal("950.00"),
        duration_seconds=36000.0,
    )
    mock_routing = MagicMock(spec=RoutingService)
    mock_routing.get_route.return_value = route_result

    assert station.location is not None
    candidate = StationCandidate(
        station_id=station.id,
        opis_id=station.opis_id,
        name=station.name,
        city=station.city,
        state=station.state,
        location=station.location,
        retail_price=station.retail_price,
        distance_from_start_miles=Decimal("300.00"),
    )
    mock_stations = MagicMock(spec=StationRepository)
    mock_stations.find_in_corridor.return_value = [candidate]

    stop_plan = FuelStopPlan(
        station_id=station.id,
        distance_from_start_miles=Decimal("300.00"),
        gallons_purchased=Decimal("50.000"),
        price_per_gallon=Decimal("3.100"),
        cost=Decimal("155.00"),
    )
    opt_result = OptimizationResult(
        stops=[stop_plan],
        total_gallons=Decimal("95.000"),
        total_cost=Decimal("155.00"),
        total_gallons_purchased=Decimal("50.000"),
    )
    mock_refuel = MagicMock(spec=RefuelOptimizationService)
    mock_refuel.optimize.return_value = opt_result

    mock_cache = MagicMock(spec=TripCacheManager)
    mock_cache.get.return_value = None

    service = TripPlanningService(
        geocoding_service=mock_geocoding,
        routing_service=mock_routing,
        station_repository=mock_stations,
        refuel_service=mock_refuel,
        trip_repository=TripPlanRepository(),
        fuel_stop_repository=FuelStopRepository(),
        cache_manager=mock_cache,
    )

    plan = service.plan_trip("Chicago, IL", "Dallas, TX")

    assert plan is not None
    assert plan.total_distance_miles == Decimal("950.00")
    assert plan.total_cost == Decimal("155.00")
    assert plan.total_gallons == Decimal("95.000")

    # Verify DB persistence
    db_plan = TripPlan.objects.get(pk=plan.id)
    assert db_plan.start_input == "Chicago, IL"
    assert db_plan.end_input == "Dallas, TX"
    assert db_plan.fuel_stops.count() == 1
    db_stop = db_plan.fuel_stops.first()
    assert db_stop is not None
    assert db_stop.station == station
    assert db_stop.gallons_purchased == Decimal("50.000")

    # Verify cache repopulation
    mock_cache.set.assert_called_once()


@pytest.mark.django_db
def test_plan_trip_geocoding_failure_propagates_without_db_writes() -> None:
    mock_geocoding = MagicMock(spec=GeocodingService)
    mock_geocoding.resolve.side_effect = GeocodingUnresolvedError("Unknown location")
    mock_cache = MagicMock(spec=TripCacheManager)
    mock_cache.get.return_value = None

    service = TripPlanningService(
        geocoding_service=mock_geocoding,
        cache_manager=mock_cache,
    )

    with pytest.raises(GeocodingUnresolvedError):
        service.plan_trip("Unknown, XX", "Dallas, TX")

    assert TripPlan.objects.count() == 0
    assert FuelStop.objects.count() == 0


@pytest.mark.django_db
def test_plan_trip_routing_failure_propagates_without_db_writes() -> None:
    mock_geocoding = MagicMock(spec=GeocodingService)
    mock_geocoding.resolve.return_value = Coordinates(
        longitude=-87.6298, latitude=41.8781
    )
    mock_routing = MagicMock(spec=RoutingService)
    mock_routing.get_route.side_effect = RoutingUnavailableError("Routing down")
    mock_cache = MagicMock(spec=TripCacheManager)
    mock_cache.get.return_value = None

    service = TripPlanningService(
        geocoding_service=mock_geocoding,
        routing_service=mock_routing,
        cache_manager=mock_cache,
    )

    with pytest.raises(RoutingUnavailableError):
        service.plan_trip("Chicago, IL", "Dallas, TX")

    assert TripPlan.objects.count() == 0


@pytest.mark.django_db
def test_plan_trip_insufficient_coverage_propagates_without_db_writes() -> None:
    start_coords = Coordinates(longitude=-87.6298, latitude=41.8781)
    end_coords = Coordinates(longitude=-96.7970, latitude=32.7767)

    mock_geocoding = MagicMock(spec=GeocodingService)
    mock_geocoding.resolve.side_effect = [start_coords, end_coords]

    route_geom = LineString(
        [(-87.6298, 41.8781), (-96.7970, 32.7767)],
        srid=4326,
    )
    mock_routing = MagicMock(spec=RoutingService)
    mock_routing.get_route.return_value = RouteResult(
        route_geometry=route_geom,
        total_distance_miles=Decimal("950.00"),
        duration_seconds=36000.0,
    )

    mock_stations = MagicMock(spec=StationRepository)
    mock_stations.find_in_corridor.return_value = []

    mock_refuel = MagicMock(spec=RefuelOptimizationService)
    mock_refuel.optimize.side_effect = InsufficientStationCoverageError(
        "Gap exceeds range"
    )

    mock_cache = MagicMock(spec=TripCacheManager)
    mock_cache.get.return_value = None

    service = TripPlanningService(
        geocoding_service=mock_geocoding,
        routing_service=mock_routing,
        station_repository=mock_stations,
        refuel_service=mock_refuel,
        cache_manager=mock_cache,
    )

    with pytest.raises(InsufficientStationCoverageError):
        service.plan_trip("Chicago, IL", "Dallas, TX")

    assert TripPlan.objects.count() == 0


@pytest.mark.django_db
def test_plan_trip_links_active_pricing_dataset_and_sets_versioned_cache_key() -> None:
    from stations.models import PricingDataset
    from trips.caching import build_trip_cache_key

    PricingDataset.objects.filter(is_active=True).update(is_active=False)
    active_ds = PricingDataset.objects.create(
        version_code="OPIS-2026-ACTIVE",
        filename="active_prices.csv",
        file_hash="hash_active_123",
        station_count=1,
        is_active=True,
    )

    station = Station.objects.create(
        opis_id="OPIS_200",
        name="Loves Active",
        city="Springfield",
        state="MO",
        retail_price=Decimal("2.999"),
        location=Point(-93.29, 37.20, srid=4326),
    )

    start_coords = Coordinates(longitude=-87.6298, latitude=41.8781)
    end_coords = Coordinates(longitude=-96.7970, latitude=32.7767)

    mock_geocoding = MagicMock(spec=GeocodingService)
    mock_geocoding.resolve.side_effect = [start_coords, end_coords]

    route_geom = LineString([(-87.6298, 41.8781), (-96.7970, 32.7767)], srid=4326)
    route_result = RouteResult(
        route_geometry=route_geom,
        total_distance_miles=Decimal("500.00"),
        duration_seconds=18000.0,
    )
    mock_routing = MagicMock(spec=RoutingService)
    mock_routing.get_route.return_value = route_result

    assert station.location is not None
    candidate = StationCandidate(
        station_id=station.id,
        opis_id=station.opis_id,
        name=station.name,
        city=station.city,
        state=station.state,
        location=station.location,
        retail_price=station.retail_price,
        distance_from_start_miles=Decimal("250.00"),
    )
    mock_stations = MagicMock(spec=StationRepository)
    mock_stations.find_in_corridor.return_value = [candidate]

    stop_plan = FuelStopPlan(
        station_id=station.id,
        distance_from_start_miles=Decimal("250.00"),
        gallons_purchased=Decimal("50.000"),
        price_per_gallon=Decimal("2.999"),
        cost=Decimal("149.95"),
    )
    opt_result = OptimizationResult(
        stops=[stop_plan],
        total_gallons=Decimal("50.000"),
        total_cost=Decimal("149.95"),
        total_gallons_purchased=Decimal("50.000"),
    )
    mock_refuel = MagicMock(spec=RefuelOptimizationService)
    mock_refuel.optimize.return_value = opt_result

    mock_cache = MagicMock(spec=TripCacheManager)
    mock_cache.get.return_value = None

    service = TripPlanningService(
        geocoding_service=mock_geocoding,
        routing_service=mock_routing,
        station_repository=mock_stations,
        refuel_service=mock_refuel,
        trip_repository=TripPlanRepository(),
        fuel_stop_repository=FuelStopRepository(),
        cache_manager=mock_cache,
    )

    plan = service.plan_trip("Chicago, IL", "Dallas, TX")

    expected_cache_key = build_trip_cache_key(
        "Chicago, IL", "Dallas, TX", version_code="OPIS-2026-ACTIVE"
    )
    assert plan.cache_key == expected_cache_key
    assert plan.pricing_dataset == active_ds

    db_plan = TripPlan.objects.get(id=plan.id)
    assert db_plan.cache_key == expected_cache_key
    assert db_plan.pricing_dataset == active_ds
