import pytest

from core.exceptions import GeocodingUnresolvedError
from routing.adapters.base import GeocodingClient
from routing.coordinates import Coordinates


class DummySuccessfulGeocoder(GeocodingClient):
    def _try_resolve(self, location_input: str) -> Coordinates | None:
        return Coordinates(longitude=-95.99, latitude=36.16)


class DummyFailingGeocoder(GeocodingClient):
    def _try_resolve(self, location_input: str) -> Coordinates | None:
        return None


class TestCoordinates:
    def test_coordinates_to_point(self) -> None:
        coords = Coordinates(longitude=-95.99, latitude=36.16)
        point = coords.to_point()

        assert point.srid == 4326
        assert point.x == -95.99
        assert point.y == 36.16


class TestGeocodingClientChain:
    def test_single_adapter_success(self) -> None:
        client = DummySuccessfulGeocoder()
        result = client.resolve("Tulsa, OK")

        assert result.longitude == -95.99
        assert result.latitude == 36.16

    def test_single_adapter_failure_raises_unresolved(self) -> None:
        client = DummyFailingGeocoder()

        with pytest.raises(GeocodingUnresolvedError, match="Unable to resolve"):
            client.resolve("Unknown City, ZZ")

    def test_delegates_to_next_link_on_failure(self) -> None:
        fallback = DummySuccessfulGeocoder()
        primary = DummyFailingGeocoder(next_link=fallback)

        result = primary.resolve("Tulsa, OK")
        assert result.longitude == -95.99
        assert result.latitude == 36.16

    def test_raises_unresolved_when_chain_exhausted(self) -> None:
        link2 = DummyFailingGeocoder()
        link1 = DummyFailingGeocoder(next_link=link2)

        with pytest.raises(GeocodingUnresolvedError, match="Unable to resolve"):
            link1.resolve("Unknown City, ZZ")
