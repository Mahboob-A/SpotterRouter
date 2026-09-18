from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from core.constants import MAX_RANGE_MILES, MPG_CONSTANT
from stations.repositories import StationCandidate
from trips.strategies import FuelStopPlan, GreedyLookaheadStrategy, RefuelStrategy


@dataclass(frozen=True)
class OptimizationResult:
    """Result of refuel stop optimization containing stops and aggregated metrics."""

    stops: list[FuelStopPlan]
    total_gallons: Decimal
    total_cost: Decimal
    total_gallons_purchased: Decimal


class RefuelOptimizationService:
    """Service owning refueling stop selection and fuel cost computation."""

    def __init__(
        self,
        strategy: RefuelStrategy | None = None,
        max_range_miles: Decimal = Decimal(str(MAX_RANGE_MILES)),
        mpg: Decimal = MPG_CONSTANT,
    ) -> None:
        self._strategy = strategy or GreedyLookaheadStrategy()
        self._max_range_miles = Decimal(str(max_range_miles))
        self._mpg = Decimal(str(mpg))

    def optimize(
        self,
        candidates: Sequence[StationCandidate],
        total_distance_miles: Decimal,
    ) -> OptimizationResult:
        """Calculate optimal refuel stops, fuel consumption, and costs."""
        stops = self._strategy.select_stops(
            candidates,
            total_distance_miles,
            self._max_range_miles,
            self._mpg,
        )

        total_gallons = Decimal(str(round(total_distance_miles / self._mpg, 3)))
        total_cost = sum((stop.cost for stop in stops), Decimal("0.00"))
        total_gallons_purchased = sum(
            (stop.gallons_purchased for stop in stops),
            Decimal("0.000"),
        )

        return OptimizationResult(
            stops=stops,
            total_gallons=total_gallons,
            total_cost=total_cost,
            total_gallons_purchased=total_gallons_purchased,
        )
