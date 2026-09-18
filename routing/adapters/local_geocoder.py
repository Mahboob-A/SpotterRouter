from typing import Any

from uszipcode import SearchEngine

from core.constants import CONTIGUOUS_48_STATES
from routing.adapters.base import GeocodingClient
from routing.coordinates import Coordinates


class LocalGeocoder(GeocodingClient):
    """Local offline geocoder using the uszipcode dataset for city/state lookups."""

    def __init__(
        self,
        next_link: GeocodingClient | None = None,
        search_engine: Any = None,
    ) -> None:
        super().__init__(next_link=next_link)
        self._search_engine = search_engine or SearchEngine()

    def _try_resolve(self, location_input: str) -> Coordinates | None:
        parts = [p.strip() for p in location_input.split(",")]
        if len(parts) != 2:
            return None

        city, state = parts[0], parts[1].upper()
        if not city or not state:
            return None

        if state not in CONTIGUOUS_48_STATES:
            return None

        try:
            results = self._search_engine.by_city_and_state(city, state)
            if not results:
                return None

            first = results[0]
            if first.lng is None or first.lat is None:
                return None

            return Coordinates(longitude=float(first.lng), latitude=float(first.lat))
        except Exception:
            return None
