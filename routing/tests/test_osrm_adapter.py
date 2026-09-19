from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import requests
from django.contrib.gis.geos import LineString, Point

from core.exceptions import RoutingUnavailableError
from routing.adapters.base import RouteResult
from routing.adapters.osrm import OSRMRoutingClient


class TestOSRMRoutingClient:
    def test_get_route_success_parses_geojson_and_distance(self) -> None:
        start = Point(-87.6298, 41.8781, srid=4326)
        end = Point(-96.7970, 32.7767, srid=4326)

        mock_payload = {
            "code": "Ok",
            "routes": [
                {
                    "geometry": {
                        "coordinates": [
                            [-87.6298, 41.8781],
                            [-90.0000, 37.0000],
                            [-96.7970, 32.7767],
                        ],
                        "type": "LineString",
                    },
                    "distance": 1556720.0,
                    "duration": 52140.0,
                }
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_payload

        client = OSRMRoutingClient(base_url="https://osrm.test/route/v1/driving")

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = client.get_route(start, end)

        assert isinstance(result, RouteResult)
        assert isinstance(result.route_geometry, LineString)
        assert result.route_geometry.srid == 4326
        assert len(result.route_geometry.coords) == 3
        assert result.total_distance_miles == Decimal("967.30")
        assert result.duration_seconds == 52140.0

        mock_get.assert_called_once_with(
            "https://osrm.test/route/v1/driving/-87.6298,41.8781;-96.797,32.7767",
            params={"overview": "full", "geometries": "geojson"},
            timeout=10.0,
        )

    def test_get_route_http_error_raises_routing_unavailable_error(self) -> None:
        start = Point(-87.6298, 41.8781, srid=4326)
        end = Point(-96.7970, 32.7767, srid=4326)

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        client = OSRMRoutingClient()
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(RoutingUnavailableError, match="503"):
                client.get_route(start, end)

    def test_get_route_connection_error_raises_routing_unavailable_error(
        self,
    ) -> None:
        start = Point(-87.6298, 41.8781, srid=4326)
        end = Point(-96.7970, 32.7767, srid=4326)

        client = OSRMRoutingClient()
        with patch(
            "requests.get",
            side_effect=requests.ConnectionError("Connection refused"),
        ):
            with pytest.raises(RoutingUnavailableError, match="Failed to connect"):
                client.get_route(start, end)

    def test_get_route_timeout_raises_routing_unavailable_error(self) -> None:
        start = Point(-87.6298, 41.8781, srid=4326)
        end = Point(-96.7970, 32.7767, srid=4326)

        client = OSRMRoutingClient()
        with patch(
            "requests.get",
            side_effect=requests.Timeout("Request timed out"),
        ):
            with pytest.raises(RoutingUnavailableError, match="Failed to connect"):
                client.get_route(start, end)

    def test_get_route_no_route_code_raises_routing_unavailable_error(
        self,
    ) -> None:
        start = Point(-87.6298, 41.8781, srid=4326)
        end = Point(-96.7970, 32.7767, srid=4326)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": "NoRoute", "routes": []}

        client = OSRMRoutingClient()
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(RoutingUnavailableError, match="NoRoute"):
                client.get_route(start, end)

    def test_get_route_invalid_json_raises_routing_unavailable_error(
        self,
    ) -> None:
        start = Point(-87.6298, 41.8781, srid=4326)
        end = Point(-96.7970, 32.7767, srid=4326)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        client = OSRMRoutingClient()
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(RoutingUnavailableError, match="invalid JSON"):
                client.get_route(start, end)
