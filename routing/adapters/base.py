from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from django.contrib.gis.geos import LineString, Point

from core.exceptions import GeocodingUnresolvedError
from routing.coordinates import Coordinates


@dataclass(frozen=True)
class RouteResult:
    route_geometry: LineString
    total_distance_miles: Decimal
    duration_seconds: float


class RoutingClient(ABC):
    """Base interface for routing adapters calculating driving directions."""

    @abstractmethod
    def get_route(self, start: Point, end: Point) -> RouteResult:
        """Calculate a driving route between two points."""


class GeocodingClient(ABC):
    """Base interface for geocoding adapters implementing Chain of Responsibility."""

    def __init__(self, next_link: "GeocodingClient | None" = None) -> None:
        self._next = next_link

    def resolve(self, location_input: str) -> Coordinates:
        """Resolve location using this link or delegate to the next link."""
        result = self._try_resolve(location_input)
        if result is not None:
            return result
        if self._next is not None:
            return self._next.resolve(location_input)
        raise GeocodingUnresolvedError(
            f"Unable to resolve location: {location_input}"
        )

    @abstractmethod
    def _try_resolve(self, location_input: str) -> Coordinates | None:
        """Attempt to resolve the input into Coordinates, or return None on miss."""
