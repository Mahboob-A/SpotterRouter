import json
import uuid
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from core.exceptions import FuelRouterError
from trips.repositories import TripPlanRepository
from trips.services import TripPlanningService
from ui.constants import PRESET_TRIP_PAIRS


class HomeView(View):
    """Presentation view for route planning input, presets, and recent trips."""

    def __init__(
        self,
        service: TripPlanningService | None = None,
        repository: TripPlanRepository | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._service = service or TripPlanningService()
        self._repository = repository or TripPlanRepository()

    def get(self, request: HttpRequest) -> HttpResponse:
        recent_trips = self._repository.list_recent(limit=20)
        context = {
            "recent_trips": recent_trips,
            "presets": PRESET_TRIP_PAIRS,
            "start": "",
            "end": "",
        }
        return render(request, "ui/home.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        start = request.POST.get("start", "").strip()
        end = request.POST.get("end", "").strip()
        recent_trips = self._repository.list_recent(limit=20)

        if not start or not end:
            context = {
                "recent_trips": recent_trips,
                "presets": PRESET_TRIP_PAIRS,
                "start": start,
                "end": end,
                "error": "Both start and destination locations are required.",
            }
            return render(request, "ui/home.html", context, status=400)

        try:
            plan = self._service.plan_trip(start_input=start, end_input=end)
            return redirect("trip-detail", trip_id=plan.id)
        except FuelRouterError as exc:
            context = {
                "recent_trips": recent_trips,
                "presets": PRESET_TRIP_PAIRS,
                "start": start,
                "end": end,
                "error": str(exc),
            }
            return render(request, "ui/home.html", context, status=400)


class TripDetailView(View):
    """Presentation view for rendering an interactive map and trip breakdown."""

    def __init__(
        self,
        repository: TripPlanRepository | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._repository = repository or TripPlanRepository()

    def get(self, request: HttpRequest, trip_id: uuid.UUID) -> HttpResponse:
        trip = self._repository.get_by_id(trip_id)
        if trip is None:
            raise Http404("Trip plan does not exist.")

        route_geojson = "{}"
        if trip.route_geometry is not None:
            if hasattr(trip.route_geometry, "geojson"):
                route_geojson = str(trip.route_geometry.geojson)
            elif isinstance(trip.route_geometry, dict):
                route_geojson = json.dumps(trip.route_geometry)
            elif isinstance(trip.route_geometry, str):
                route_geojson = trip.route_geometry

        fuel_stops = list(
            trip.fuel_stops.all().select_related("station").order_by("stop_order")
        )

        stops_data: list[dict[str, Any]] = []
        for stop in fuel_stops:
            lat = float(stop.station.location.y) if stop.station.location else 0.0
            lng = float(stop.station.location.x) if stop.station.location else 0.0
            stops_data.append(
                {
                    "stop_order": stop.stop_order,
                    "station_name": stop.station.name,
                    "city": stop.station.city,
                    "state": stop.station.state,
                    "lat": lat,
                    "lng": lng,
                    "distance_from_start_miles": float(
                        stop.distance_from_start_miles
                    ),
                    "gallons_purchased": float(stop.gallons_purchased),
                    "price_per_gallon": float(stop.price_per_gallon),
                    "cost": float(stop.cost),
                }
            )

        origin_lat = float(trip.start_point.y) if trip.start_point else 0.0
        origin_lng = float(trip.start_point.x) if trip.start_point else 0.0
        dest_lat = float(trip.end_point.y) if trip.end_point else 0.0
        dest_lng = float(trip.end_point.x) if trip.end_point else 0.0

        context = {
            "trip": trip,
            "route_geojson": route_geojson,
            "fuel_stops": fuel_stops,
            "stops_json": json.dumps(stops_data),
            "origin_lat": origin_lat,
            "origin_lng": origin_lng,
            "dest_lat": dest_lat,
            "dest_lng": dest_lng,
        }
        return render(request, "ui/trip_detail.html", context)
