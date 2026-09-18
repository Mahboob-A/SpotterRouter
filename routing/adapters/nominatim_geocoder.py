import os
from typing import Any

import requests

from core.constants import CONTIGUOUS_48_STATES
from routing.adapters.base import GeocodingClient
from routing.coordinates import Coordinates

DEFAULT_NOMINATIM_USER_AGENT = "fuel-router/1.0"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


class NominatimGeocoder(GeocodingClient):
    """Fallback geocoder calling the OpenStreetMap Nominatim HTTP service."""

    def __init__(
        self,
        next_link: GeocodingClient | None = None,
        user_agent: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        super().__init__(next_link=next_link)
        self._user_agent = (
            user_agent
            or os.environ.get("NOMINATIM_USER_AGENT")
            or DEFAULT_NOMINATIM_USER_AGENT
        )
        self._timeout = timeout_seconds

    def _try_resolve(self, location_input: str) -> Coordinates | None:
        params: dict[str, str] = {
            "q": location_input,
            "format": "json",
            "countrycodes": "us",
            "limit": "1",
            "addressdetails": "1",
        }
        headers = {"User-Agent": self._user_agent}

        try:
            response = requests.get(
                NOMINATIM_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=self._timeout,
            )
            if response.status_code != 200:
                return None

            data: Any = response.json()
            if not isinstance(data, list) or not data:
                return None

            first = data[0]
            if not self._is_in_scope(first.get("address", {})):
                return None

            return Coordinates(
                longitude=float(first["lon"]),
                latitude=float(first["lat"]),
            )
        except (requests.RequestException, KeyError, ValueError, TypeError):
            return None

    def _is_in_scope(self, address: dict[str, Any]) -> bool:
        iso_code = str(address.get("ISO3166-2-lvl4", ""))
        if iso_code.startswith("US-"):
            state_code = iso_code.split("-")[-1].upper()
            return state_code in CONTIGUOUS_48_STATES

        state_name = str(address.get("state", ""))
        out_of_scope_names = {
            "alaska",
            "hawaii",
            "puerto rico",
            "guam",
            "us virgin islands",
            "virgin islands",
        }
        if state_name.lower() in out_of_scope_names:
            return False

        return True
