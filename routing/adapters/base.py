from abc import ABC, abstractmethod

from core.exceptions import GeocodingUnresolvedError
from routing.coordinates import Coordinates


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
        raise GeocodingUnresolvedError(f"Unable to resolve location: {location_input}")

    @abstractmethod
    def _try_resolve(self, location_input: str) -> Coordinates | None:
        """Attempt to resolve the input into Coordinates, or return None on miss."""
