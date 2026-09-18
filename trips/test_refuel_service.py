from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.contrib.gis.geos import Point

from core.exceptions import InsufficientStationCoverageError
from stations.repositories import StationCandidate
from trips.services import OptimizationResult, RefuelOptimizationService
from trips.strategies import FuelStopPlan, RefuelStrategy


def _create_candidate(
    station_id: int,
    distance_from_start: str,
    price: str,
) -> StationCandidate:
    return StationCandidate(
        station_id=station_id,
        opis_id=f"OPIS_{station_id}",
        name=f"Station {station_id}",
        city="Sample City",
        state="IL",
        location=Point(-88.0, 42.0, srid=4326),
        retail_price=Decimal(price),
        distance_from_start_miles=Decimal(distance_from_start),
    )


def test_optimization_result_dataclass_properties() -> None:
    stop = FuelStopPlan(
        station_id=1,
        distance_from_start_miles=Decimal("400.00"),
        gallons_purchased=Decimal("35.000"),
        price_per_gallon=Decimal("3.500"),
        cost=Decimal("122.50"),
    )
    result = OptimizationResult(
        stops=[stop],
        total_gallons=Decimal("75.000"),
        total_cost=Decimal("122.50"),
        total_gallons_purchased=Decimal("35.000"),
    )
    assert len(result.stops) == 1
    assert result.total_gallons == Decimal("75.000")
    assert result.total_cost == Decimal("122.50")
    assert result.total_gallons_purchased == Decimal("35.000")


def test_refuel_service_short_trip_no_stops() -> None:
    service = RefuelOptimizationService()
    candidates = [
        _create_candidate(1, "200.00", "3.500"),
    ]
    result = service.optimize(candidates, total_distance_miles=Decimal("300.00"))

    assert result.stops == []
    assert result.total_cost == Decimal("0.00")
    assert result.total_gallons_purchased == Decimal("0.000")
    assert result.total_gallons == Decimal("30.000")


def test_refuel_service_aggregates_stops_and_costs() -> None:
    service = RefuelOptimizationService()
    candidates = [
        _create_candidate(1, "400.00", "3.200"),
        _create_candidate(2, "750.00", "3.100"),
    ]
    result = service.optimize(candidates, total_distance_miles=Decimal("900.00"))

    assert len(result.stops) > 0
    expected_cost = sum((s.cost for s in result.stops), Decimal("0.00"))
    expected_purchased = sum(
        (s.gallons_purchased for s in result.stops), Decimal("0.000")
    )
    assert result.total_cost == expected_cost
    assert result.total_gallons_purchased == expected_purchased
    assert result.total_gallons == Decimal("90.000")


def test_refuel_service_honors_injected_strategy_and_parameters() -> None:
    mock_strategy = MagicMock(spec=RefuelStrategy)
    mock_stop = FuelStopPlan(
        station_id=42,
        distance_from_start_miles=Decimal("250.00"),
        gallons_purchased=Decimal("20.000"),
        price_per_gallon=Decimal("3.000"),
        cost=Decimal("60.00"),
    )
    mock_strategy.select_stops.return_value = [mock_stop]

    custom_max_range = Decimal("600")
    custom_mpg = Decimal("8.0")
    service = RefuelOptimizationService(
        strategy=mock_strategy,
        max_range_miles=custom_max_range,
        mpg=custom_mpg,
    )

    candidates = [_create_candidate(42, "250.00", "3.000")]
    result = service.optimize(candidates, total_distance_miles=Decimal("800.00"))

    mock_strategy.select_stops.assert_called_once_with(
        candidates,
        Decimal("800.00"),
        custom_max_range,
        custom_mpg,
    )
    assert result.stops == [mock_stop]
    assert result.total_cost == Decimal("60.00")
    assert result.total_gallons_purchased == Decimal("20.000")
    assert result.total_gallons == Decimal("100.000")


def test_refuel_service_propagates_unreachable_gap_error() -> None:
    service = RefuelOptimizationService()
    candidates = [
        _create_candidate(1, "600.00", "3.000"),
    ]
    with pytest.raises(InsufficientStationCoverageError):
        service.optimize(candidates, total_distance_miles=Decimal("800.00"))
