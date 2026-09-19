import pytest

from core.exceptions import GeocodingUnresolvedError
from routing.adapters.base import GeocodingClient
from routing.adapters.local_geocoder import LocalGeocoder
from routing.coordinates import Coordinates


class DummyFallbackGeocoder(GeocodingClient):
    def _try_resolve(self, location_input: str) -> Coordinates | None:
        return Coordinates(longitude=-100.0, latitude=40.0)


class TestLocalGeocoder:
    def test_resolves_clean_city_state(self) -> None:
        geocoder = LocalGeocoder()
        coords = geocoder.resolve("Tulsa, OK")

        assert isinstance(coords, Coordinates)
        assert round(coords.longitude, 1) == -96.0
        assert round(coords.latitude, 1) == 36.2

    def test_resolves_whitespace_and_case_variations(self) -> None:
        geocoder = LocalGeocoder()
        coords = geocoder.resolve("  tulsa , ok  ")

        assert isinstance(coords, Coordinates)
        assert round(coords.longitude, 1) == -96.0
        assert round(coords.latitude, 1) == 36.2

    def test_rejects_out_of_scope_state(self) -> None:
        geocoder = LocalGeocoder()

        with pytest.raises(GeocodingUnresolvedError, match="Unable to resolve"):
            geocoder.resolve("Anchorage, AK")

    def test_rejects_non_contiguous_territory(self) -> None:
        geocoder = LocalGeocoder()

        with pytest.raises(GeocodingUnresolvedError, match="Unable to resolve"):
            geocoder.resolve("San Juan, PR")

    def test_unresolvable_city_returns_none_or_delegates(self) -> None:
        fallback = DummyFallbackGeocoder()
        geocoder = LocalGeocoder(next_link=fallback)

        coords = geocoder.resolve("DefinitelyNoSuchCity12345, OK")
        assert coords.longitude == -100.0
        assert coords.latitude == 40.0

    def test_unresolvable_city_without_next_link_raises(self) -> None:
        geocoder = LocalGeocoder()

        with pytest.raises(GeocodingUnresolvedError, match="Unable to resolve"):
            geocoder.resolve("DefinitelyNoSuchCity12345, OK")

    def test_invalid_format_raises_unresolved(self) -> None:
        geocoder = LocalGeocoder()

        with pytest.raises(GeocodingUnresolvedError, match="Unable to resolve"):
            geocoder.resolve("JustAStringWithNoComma")
