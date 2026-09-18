from unittest.mock import MagicMock, patch

import pytest
import requests

from core.exceptions import GeocodingUnresolvedError
from routing.adapters.nominatim_geocoder import NominatimGeocoder
from routing.coordinates import Coordinates


class TestNominatimGeocoder:
    @patch("routing.adapters.nominatim_geocoder.requests.get")
    def test_resolves_location_successfully(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "lon": "-95.9928",
                "lat": "36.1540",
                "address": {
                    "state": "Oklahoma",
                    "ISO3166-2-lvl4": "US-OK",
                },
            }
        ]
        mock_get.return_value = mock_response

        geocoder = NominatimGeocoder()
        coords = geocoder.resolve("Tulsa, OK")

        assert isinstance(coords, Coordinates)
        assert coords.longitude == -95.9928
        assert coords.latitude == 36.1540
        assert mock_get.call_count == 1

    @patch("routing.adapters.nominatim_geocoder.requests.get")
    def test_sends_configured_user_agent(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"lon": "-95.0", "lat": "36.0", "address": {"ISO3166-2-lvl4": "US-OK"}}
        ]
        mock_get.return_value = mock_response

        geocoder = NominatimGeocoder(user_agent="custom-fuel-agent/1.0")
        geocoder.resolve("Tulsa, OK")

        mock_get.assert_called_once()
        headers = mock_get.call_args.kwargs.get("headers", {})
        assert headers.get("User-Agent") == "custom-fuel-agent/1.0"

    @patch("routing.adapters.nominatim_geocoder.requests.get")
    def test_returns_none_or_raises_on_empty_results(
        self,
        mock_get: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        geocoder = NominatimGeocoder()
        with pytest.raises(GeocodingUnresolvedError, match="Unable to resolve"):
            geocoder.resolve("Nonexistent Place")

    @patch("routing.adapters.nominatim_geocoder.requests.get")
    def test_handles_http_error_gracefully(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        geocoder = NominatimGeocoder()
        with pytest.raises(GeocodingUnresolvedError, match="Unable to resolve"):
            geocoder.resolve("Tulsa, OK")

    @patch("routing.adapters.nominatim_geocoder.requests.get")
    def test_handles_request_timeout(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.Timeout("Network timeout")

        geocoder = NominatimGeocoder()
        with pytest.raises(GeocodingUnresolvedError, match="Unable to resolve"):
            geocoder.resolve("Tulsa, OK")

    @patch("routing.adapters.nominatim_geocoder.requests.get")
    def test_rejects_out_of_scope_state(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "lon": "-149.9003",
                "lat": "61.2181",
                "address": {
                    "state": "Alaska",
                    "ISO3166-2-lvl4": "US-AK",
                },
            }
        ]
        mock_get.return_value = mock_response

        geocoder = NominatimGeocoder()
        with pytest.raises(GeocodingUnresolvedError, match="Unable to resolve"):
            geocoder.resolve("Anchorage, AK")
