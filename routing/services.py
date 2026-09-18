from django.contrib.gis.geos import Point

from routing.adapters.base import GeocodingClient
from routing.adapters.local_geocoder import LocalGeocoder
from routing.adapters.nominatim_geocoder import NominatimGeocoder
from routing.coordinates import Coordinates


class GeocodingService:
    """Service orchestrating geocoding via Chain of Responsibility."""

    def __init__(self, chain: GeocodingClient | None = None) -> None:
        self._chain = chain or LocalGeocoder(next_link=NominatimGeocoder())

    def resolve(self, location_input: str) -> Coordinates:
        """Resolve an address or city/state input to normalized Coordinates."""
        return self._chain.resolve(location_input)

    def resolve_point(self, location_input: str) -> Point:
        """Resolve an address or city/state input to an SRID 4326 PostGIS Point."""
        coordinates = self.resolve(location_input)
        return coordinates.to_point()
