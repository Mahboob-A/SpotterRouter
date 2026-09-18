from unittest.mock import MagicMock

import pytest
from django.contrib.gis.geos import Point

from core.exceptions import GeocodingUnresolvedError
from routing.adapters.base import GeocodingClient
from routing.coordinates import Coordinates
from routing.services import GeocodingService


class DummyLocalGeocoder(GeocodingClient):
    def __init__(
        self,
        return_value: Coordinates | None = None,
        next_link: GeocodingClient | None = None,
    ) -> None:
        super().__init__(next_link=next_link)
        self.return_value = return_value
        self.call_count = 0

    def _try_resolve(self, location_input: str) -> Coordinates | None:
        self.call_count += 1
        return self.return_value


class DummyFallbackGeocoder(GeocodingClient):
    def __init__(
        self,
        return_value: Coordinates | None = None,
        next_link: GeocodingClient | None = None,
    ) -> None:
        super().__init__(next_link=next_link)
        self.return_value = return_value
        self.call_count = 0

    def _try_resolve(self, location_input: str) -> Coordinates | None:
        self.call_count += 1
        return self.return_value


class TestGeocodingService:
    def test_local_success_prevents_fallback(self) -> None:
        fallback = DummyFallbackGeocoder(return_value=Coordinates(0.0, 0.0))
        local = DummyLocalGeocoder(
            return_value=Coordinates(-95.99, 36.16),
            next_link=fallback,
        )
        service = GeocodingService(chain=local)

        result = service.resolve("Tulsa, OK")

        assert result.longitude == -95.99
        assert result.latitude == 36.16
        assert local.call_count == 1
        assert fallback.call_count == 0

    def test_local_failure_triggers_fallback_once(self) -> None:
        fallback = DummyFallbackGeocoder(
            return_value=Coordinates(-95.99, 36.16),
        )
        local = DummyLocalGeocoder(return_value=None, next_link=fallback)
        service = GeocodingService(chain=local)

        result = service.resolve("Tulsa, OK")

        assert result.longitude == -95.99
        assert result.latitude == 36.16
        assert local.call_count == 1
        assert fallback.call_count == 1

    def test_exhausted_chain_raises_unresolved(self) -> None:
        fallback = DummyFallbackGeocoder(return_value=None)
        local = DummyLocalGeocoder(return_value=None, next_link=fallback)
        service = GeocodingService(chain=local)

        with pytest.raises(GeocodingUnresolvedError, match="Unable to resolve"):
            service.resolve("Unresolvable Location")

        assert local.call_count == 1
        assert fallback.call_count == 1

    def test_resolve_point_returns_srid_4326_point(self) -> None:
        local = DummyLocalGeocoder(return_value=Coordinates(-95.99, 36.16))
        service = GeocodingService(chain=local)

        point = service.resolve_point("Tulsa, OK")

        assert isinstance(point, Point)
        assert point.srid == 4326
        assert point.x == -95.99
        assert point.y == 36.16
