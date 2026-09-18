from decimal import Decimal
from unittest.mock import MagicMock

from django.contrib.gis.geos import LineString, Point
import pytest

from core.exceptions import RoutingUnavailableError
from routing.adapters.base import RouteResult, RoutingClient
from routing.adapters.osrm import OSRMRoutingClient
from routing.services import RoutingService


class TestRoutingService:
    def test_default_client_is_osrm_routing_client(self) -> None:
        service = RoutingService()
        assert isinstance(service.client, OSRMRoutingClient)

    def test_get_route_delegates_to_injected_client(self) -> None:
        mock_client = MagicMock(spec=RoutingClient)
        start = Point(-87.6298, 41.8781, srid=4326)
        end = Point(-96.7970, 32.7767, srid=4326)
        expected_line = LineString([start, end], srid=4326)
        expected_result = RouteResult(
            route_geometry=expected_line,
            total_distance_miles=Decimal("967.30"),
            duration_seconds=50000.0,
        )
        mock_client.get_route.return_value = expected_result

        service = RoutingService(client=mock_client)
        result = service.get_route(start, end)

        assert result == expected_result
        mock_client.get_route.assert_called_once_with(start, end)

    def test_get_route_propagates_routing_unavailable_error(self) -> None:
        mock_client = MagicMock(spec=RoutingClient)
        start = Point(-87.6298, 41.8781, srid=4326)
        end = Point(-96.7970, 32.7767, srid=4326)
        mock_client.get_route.side_effect = RoutingUnavailableError(
            "Service down"
        )

        service = RoutingService(client=mock_client)
        with pytest.raises(RoutingUnavailableError, match="Service down"):
            service.get_route(start, end)
