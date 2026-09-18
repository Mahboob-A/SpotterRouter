import os
from decimal import Decimal

import requests
from django.contrib.gis.geos import LineString, Point

from core.exceptions import RoutingUnavailableError
from routing.adapters.base import RouteResult, RoutingClient


class OSRMRoutingClient(RoutingClient):
    """Routing client adapter connecting to Open Source Routing Machine (OSRM)."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get(
                "OSRM_BASE_URL",
                "https://router.project-osrm.org/route/v1/driving",
            )
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_route(self, start: Point, end: Point) -> RouteResult:
        """Fetch driving directions between two points from OSRM API."""
        coords_param = f"{start.x},{start.y};{end.x},{end.y}"
        url = f"{self.base_url}/{coords_param}"
        params = {
            "overview": "full",
            "geometries": "geojson",
        }

        try:
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise RoutingUnavailableError(
                f"Failed to connect to OSRM routing service: {exc}"
            ) from exc

        if response.status_code != 200:
            raise RoutingUnavailableError(
                f"OSRM service returned HTTP status {response.status_code}: "
                f"{response.text}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise RoutingUnavailableError(
                f"OSRM service returned invalid JSON response: {exc}"
            ) from exc

        if data.get("code") != "Ok" or not data.get("routes"):
            code = data.get("code", "Unknown")
            raise RoutingUnavailableError(
                f"OSRM route calculation failed with code: {code}"
            )

        route = data["routes"][0]
        geometry_data = route.get("geometry", {})
        coordinates = geometry_data.get("coordinates")
        if not coordinates or not isinstance(coordinates, list):
            raise RoutingUnavailableError(
                "OSRM response did not contain route geometry coordinates"
            )

        # OSRM coordinates are [lon, lat], corresponding to Point(x=lon, y=lat)
        line = LineString(coordinates, srid=4326)

        # OSRM distance is in meters; 1 meter = 1 / 1609.344 miles
        distance_meters = float(route.get("distance", 0.0))
        distance_miles = Decimal(str(round(distance_meters / 1609.344, 2)))
        duration_seconds = float(route.get("duration", 0.0))

        return RouteResult(
            route_geometry=line,
            total_distance_miles=distance_miles,
            duration_seconds=duration_seconds,
        )
