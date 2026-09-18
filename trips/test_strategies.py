from decimal import Decimal

from django.contrib.gis.geos import Point
import pytest

from core.exceptions import InsufficientStationCoverageError
from stations.repositories import StationCandidate
from trips.strategies import (
    FuelStopPlan,
    GreedyLookaheadStrategy,
    RefuelStrategy,
)


def _make_candidate(
    station_id: int,
    distance_miles: Decimal | str | float,
    price: Decimal | str | float,
) -> StationCandidate:
    dist = Decimal(str(distance_miles))
    pr = Decimal(str(price))
    return StationCandidate(
        station_id=station_id,
        opis_id=f"OPIS-{station_id}",
        name=f"Station {station_id}",
        city="TestCity",
        state="TX",
        location=Point(-95.0, 30.0, srid=4326),
        retail_price=pr,
        distance_from_start_miles=dist,
    )


class TestGreedyLookaheadStrategy:
    def test_implements_refuel_strategy_interface(self) -> None:
        strategy = GreedyLookaheadStrategy()
        assert isinstance(strategy, RefuelStrategy)

    def test_short_route_under_max_range_requires_zero_stops(self) -> None:
        strategy = GreedyLookaheadStrategy()
        candidates = [
            _make_candidate(1, 100, "3.500"),
            _make_candidate(2, 250, "3.200"),
        ]
        stops = strategy.select_stops(
            candidates=candidates,
            total_distance_miles=Decimal("400.00"),
            max_range_miles=Decimal("500.00"),
            mpg=Decimal("10.00"),
        )
        assert stops == []

    def test_single_stop_route_buys_only_necessary_fuel_to_destination(
        self,
    ) -> None:
        strategy = GreedyLookaheadStrategy()
        candidates = [
            _make_candidate(1, 250, "3.500"),
            _make_candidate(2, 400, "3.200"),
            _make_candidate(3, 600, "3.800"),
        ]
        # Route 800 miles. From mile 0, can reach S1 (250) and S2 (400).
        # S2 is cheaper (3.20). Departs mile 0 at no cost.
        # Arrives at S2 (mile 400) with 100 miles of remaining range.
        # Destination is 800 (400 miles away). S3 (600) is more expensive (3.80).
        # Buys fuel at S2 to reach destination: (400 - 100) / 10 = 30 gallons.
        stops = strategy.select_stops(
            candidates=candidates,
            total_distance_miles=Decimal("800.00"),
            max_range_miles=Decimal("500.00"),
            mpg=Decimal("10.00"),
        )

        assert len(stops) == 1
        stop = stops[0]
        assert isinstance(stop, FuelStopPlan)
        assert stop.station_id == 2
        assert stop.distance_from_start_miles == Decimal("400.00")
        assert stop.gallons_purchased == Decimal("30.000")
        assert stop.price_per_gallon == Decimal("3.200")
        assert stop.cost == Decimal("96.00")

    def test_multiple_stops_prioritizes_cheaper_stations_ahead(self) -> None:
        strategy = GreedyLookaheadStrategy()
        candidates = [
            _make_candidate(1, 300, "3.500"),
            _make_candidate(2, 400, "3.000"),
            _make_candidate(3, 700, "2.800"),
        ]
        # Route 1000 miles.
        # Mile 0: reachable S1(300), S2(400). Cheapest is S2 (3.00).
        # At S2 (400, remaining 100): reachable S3 (700, 2.80).
        # S3 is cheaper than S2 (2.80 < 3.00).
        # Buys enough at S2 to reach S3 with empty tank: (300 - 100) / 10 = 20 gal.
        # Cost at S2: 20 * 3.00 = $60.00.
        # At S3 (700, remaining 0): destination is 1000 (300 miles away <= 500).
        # Buys enough at S3 to reach destination: 300 / 10 = 30 gal.
        # Cost at S3: 30 * 2.80 = $84.00.
        stops = strategy.select_stops(
            candidates=candidates,
            total_distance_miles=Decimal("1000.00"),
            max_range_miles=Decimal("500.00"),
            mpg=Decimal("10.00"),
        )

        assert len(stops) == 2
        assert stops[0].station_id == 2
        assert stops[0].gallons_purchased == Decimal("20.000")
        assert stops[0].cost == Decimal("60.00")

        assert stops[1].station_id == 3
        assert stops[1].gallons_purchased == Decimal("30.000")
        assert stops[1].cost == Decimal("84.00")

    def test_unreachable_gap_between_stations_raises_insufficient_coverage_error(
        self,
    ) -> None:
        strategy = GreedyLookaheadStrategy()
        candidates = [
            _make_candidate(1, 200, "3.500"),
            _make_candidate(2, 800, "3.200"),  # gap of 600 miles
        ]
        with pytest.raises(InsufficientStationCoverageError):
            strategy.select_stops(
                candidates=candidates,
                total_distance_miles=Decimal("1000.00"),
                max_range_miles=Decimal("500.00"),
                mpg=Decimal("10.00"),
            )

    def test_first_station_beyond_max_range_raises_insufficient_coverage_error(
        self,
    ) -> None:
        strategy = GreedyLookaheadStrategy()
        candidates = [
            _make_candidate(1, 550, "3.200"),  # first station at 550 miles
        ]
        with pytest.raises(InsufficientStationCoverageError):
            strategy.select_stops(
                candidates=candidates,
                total_distance_miles=Decimal("800.00"),
                max_range_miles=Decimal("500.00"),
                mpg=Decimal("10.00"),
            )

    def test_no_stations_on_long_route_raises_insufficient_coverage_error(
        self,
    ) -> None:
        strategy = GreedyLookaheadStrategy()
        with pytest.raises(InsufficientStationCoverageError):
            strategy.select_stops(
                candidates=[],
                total_distance_miles=Decimal("900.00"),
                max_range_miles=Decimal("500.00"),
                mpg=Decimal("10.00"),
            )
