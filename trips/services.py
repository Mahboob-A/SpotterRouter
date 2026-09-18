from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from core.constants import CORRIDOR_BUFFER_MILES, MAX_RANGE_MILES, MPG_CONSTANT
from routing.services import GeocodingService, RoutingService
from stations.repositories import StationCandidate, StationRepository
from trips.caching import TripCacheManager, build_trip_cache_key
from trips.models import FuelStop, TripPlan
from trips.repositories import FuelStopRepository, TripPlanRepository
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


class TripPlanningService:
    """Service orchestrating end-to-end trip computation and persistence."""

    def __init__(
        self,
        geocoding_service: GeocodingService | None = None,
        routing_service: RoutingService | None = None,
        station_repository: StationRepository | None = None,
        refuel_service: RefuelOptimizationService | None = None,
        trip_repository: TripPlanRepository | None = None,
        fuel_stop_repository: FuelStopRepository | None = None,
        cache_manager: TripCacheManager | None = None,
        corridor_buffer_miles: Decimal = CORRIDOR_BUFFER_MILES,
    ) -> None:
        self._geocoding = geocoding_service or GeocodingService()
        self._routing = routing_service or RoutingService()
        self._stations = station_repository or StationRepository()
        self._refuel = refuel_service or RefuelOptimizationService()
        self._trips = trip_repository or TripPlanRepository()
        self._fuel_stops = fuel_stop_repository or FuelStopRepository()
        self._cache_manager = cache_manager or TripCacheManager()
        self._corridor_buffer_miles = corridor_buffer_miles

    def plan_trip(self, start_input: str, end_input: str) -> TripPlan:
        """Compute an optimal fuel-stop route or retrieve a cached plan."""
        cache_key = build_trip_cache_key(start_input, end_input)

        cached_plan = self._cache_manager.get(cache_key)
        if cached_plan is not None:
            return cached_plan

        start_coords = self._geocoding.resolve(start_input)
        end_coords = self._geocoding.resolve(end_input)
        start_point = start_coords.to_point()
        end_point = end_coords.to_point()

        route_result = self._routing.get_route(start_point, end_point)

        candidates = self._stations.find_in_corridor(
            route_geometry=route_result.route_geometry,
            buffer_miles=self._corridor_buffer_miles,
            total_route_distance_miles=route_result.total_distance_miles,
        )

        opt_result = self._refuel.optimize(
            candidates,
            route_result.total_distance_miles,
        )

        with transaction.atomic():
            trip_plan = TripPlan(
                start_input=start_input,
                end_input=end_input,
                start_point=start_point,
                end_point=end_point,
                route_geometry=route_result.route_geometry,
                total_distance_miles=route_result.total_distance_miles,
                total_gallons=opt_result.total_gallons,
                total_cost=opt_result.total_cost,
                cache_key=cache_key,
            )
            saved_plan = self._trips.save(trip_plan)

            fuel_stops: list[FuelStop] = [
                FuelStop(
                    trip_plan=saved_plan,
                    station_id=stop.station_id,
                    stop_order=idx,
                    distance_from_start_miles=stop.distance_from_start_miles,
                    gallons_purchased=stop.gallons_purchased,
                    price_per_gallon=stop.price_per_gallon,
                    cost=stop.cost,
                )
                for idx, stop in enumerate(opt_result.stops, start=1)
            ]
            if fuel_stops:
                self._fuel_stops.save_many(fuel_stops)

        persisted_plan = self._trips.get_by_id(saved_plan.id) or saved_plan
        self._cache_manager.set(persisted_plan)

        try:
            from explanations.tasks import (  # type: ignore[import-not-found]
                generate_trip_explanation,
            )

            generate_trip_explanation.delay(str(persisted_plan.id))
        except (ImportError, Exception):
            pass

        return persisted_plan
