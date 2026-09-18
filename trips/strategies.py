from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from core.constants import MAX_RANGE_MILES, MPG_CONSTANT
from core.exceptions import InsufficientStationCoverageError
from stations.repositories import StationCandidate


@dataclass(frozen=True)
class FuelStopPlan:
    station_id: int
    distance_from_start_miles: Decimal
    gallons_purchased: Decimal
    price_per_gallon: Decimal
    cost: Decimal


class RefuelStrategy(ABC):
    """Abstract base class for optimal refueling stop selection strategies."""

    @abstractmethod
    def select_stops(
        self,
        candidates: Sequence[StationCandidate],
        total_distance_miles: Decimal,
        max_range_miles: Decimal = Decimal(str(MAX_RANGE_MILES)),
        mpg: Decimal = MPG_CONSTANT,
    ) -> list[FuelStopPlan]:
        """Select optimal fuel stops along a route."""


class GreedyLookaheadStrategy(RefuelStrategy):
    """Greedy-with-lookahead strategy solving the vehicle refueling problem."""

    def select_stops(
        self,
        candidates: Sequence[StationCandidate],
        total_distance_miles: Decimal,
        max_range_miles: Decimal = Decimal(str(MAX_RANGE_MILES)),
        mpg: Decimal = MPG_CONSTANT,
    ) -> list[FuelStopPlan]:
        if total_distance_miles <= Decimal("0"):
            return []

        max_range = Decimal(str(max_range_miles))
        fuel_mpg = Decimal(str(mpg))

        ordered = sorted(candidates, key=lambda c: c.distance_from_start_miles)
        stops: list[FuelStopPlan] = []

        position = Decimal("0")
        remaining_range = max_range
        current_station: StationCandidate | None = None

        while position + remaining_range < total_distance_miles:
            reachable = [
                c
                for c in ordered
                if position
                < c.distance_from_start_miles
                <= position + max_range
            ]

            dist_to_dest = total_distance_miles - position
            dest_reachable = dist_to_dest <= max_range

            if not reachable and not dest_reachable:
                raise InsufficientStationCoverageError(
                    f"No station reachable from mile {position}"
                )

            cheaper_ahead = (
                [
                    c
                    for c in reachable
                    if c.retail_price < current_station.retail_price
                ]
                if current_station is not None
                else []
            )

            if (
                current_station is not None
                and dest_reachable
                and not cheaper_ahead
            ):
                leg_miles = dist_to_dest
                gallons_needed = max(
                    Decimal("0"), (leg_miles - remaining_range) / fuel_mpg
                )
                gallons_purchased = Decimal(str(round(gallons_needed, 3)))
                if gallons_purchased > Decimal("0"):
                    cost = Decimal(
                        str(
                            round(
                                gallons_purchased
                                * current_station.retail_price,
                                2,
                            )
                        )
                    )
                    stops.append(
                        FuelStopPlan(
                            station_id=current_station.station_id,
                            distance_from_start_miles=(
                                current_station.distance_from_start_miles
                            ),
                            gallons_purchased=gallons_purchased,
                            price_per_gallon=current_station.retail_price,
                            cost=cost,
                        )
                    )
                remaining_range = (
                    remaining_range + gallons_purchased * fuel_mpg - leg_miles
                )
                position = total_distance_miles
                break

            if cheaper_ahead:
                target = min(
                    cheaper_ahead, key=lambda c: c.distance_from_start_miles
                )
                leg_miles = target.distance_from_start_miles - position
                gallons_needed = max(
                    Decimal("0"), (leg_miles - remaining_range) / fuel_mpg
                )
            else:
                target = min(
                    reachable,
                    key=lambda c: (c.retail_price, -c.distance_from_start_miles),
                )
                leg_miles = target.distance_from_start_miles - position
                gallons_needed = max(
                    Decimal("0"), (max_range - remaining_range) / fuel_mpg
                )

            gallons_purchased = Decimal(str(round(gallons_needed, 3)))
            if gallons_purchased > Decimal("0") and current_station is not None:
                cost = Decimal(
                    str(
                        round(
                            gallons_purchased * current_station.retail_price,
                            2,
                        )
                    )
                )
                stops.append(
                    FuelStopPlan(
                        station_id=current_station.station_id,
                        distance_from_start_miles=(
                            current_station.distance_from_start_miles
                        ),
                        gallons_purchased=gallons_purchased,
                        price_per_gallon=current_station.retail_price,
                        cost=cost,
                    )
                )

            remaining_range = (
                remaining_range + gallons_purchased * fuel_mpg - leg_miles
            )
            position = target.distance_from_start_miles
            current_station = target

        return stops
