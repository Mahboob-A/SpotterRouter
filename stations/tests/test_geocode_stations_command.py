import io
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.core.management.base import CommandError

from core.exceptions import GeocodingUnresolvedError
from stations.models import Station


@pytest.mark.django_db
class TestGeocodeStationsCommand:
    def test_skips_stations_with_existing_location(self) -> None:
        Station.objects.create(
            opis_id="101",
            name="Existing Station",
            city="Tulsa",
            state="OK",
            retail_price=Decimal("3.100"),
            location=Point(-95.9928, 36.1540, srid=4326),
        )
        Station.objects.create(
            opis_id="102",
            name="Ungeocoded Station",
            city="Dallas",
            state="TX",
            retail_price=Decimal("2.950"),
            location=None,
        )

        out = io.StringIO()
        with patch("routing.services.GeocodingService.resolve_point") as mock_resolve:
            mock_resolve.return_value = Point(-96.7970, 32.7767, srid=4326)
            call_command("geocode_stations", stdout=out)

            mock_resolve.assert_called_once_with("Dallas, TX")

        station_101 = Station.objects.get(opis_id="101")
        station_102 = Station.objects.get(opis_id="102")
        assert station_101.location == Point(-95.9928, 36.1540, srid=4326)
        assert station_102.location == Point(-96.7970, 32.7767, srid=4326)

        output = out.getvalue()
        assert "Total considered: 2" in output
        assert "Geocoded: 1" in output
        assert "Skipped: 1" in output
        assert "Unresolved: 0" in output

    def test_geocodes_all_ungeocoded_stations(self) -> None:
        Station.objects.create(
            opis_id="201",
            name="Station A",
            city="Tulsa",
            state="OK",
            retail_price=Decimal("3.100"),
        )
        Station.objects.create(
            opis_id="202",
            name="Station B",
            city="Dallas",
            state="TX",
            retail_price=Decimal("2.950"),
        )

        def side_effect(loc: str) -> Point:
            if "Tulsa" in loc:
                return Point(-95.9928, 36.1540, srid=4326)
            return Point(-96.7970, 32.7767, srid=4326)

        out = io.StringIO()
        with patch(
            "routing.services.GeocodingService.resolve_point",
            side_effect=side_effect,
        ):
            call_command("geocode_stations", stdout=out)

        s1 = Station.objects.get(opis_id="201")
        s2 = Station.objects.get(opis_id="202")
        assert s1.location is not None
        assert s1.location.srid == 4326
        assert s2.location is not None
        assert s2.location.srid == 4326

        output = out.getvalue()
        assert "Total considered: 2" in output
        assert "Geocoded: 2" in output
        assert "Skipped: 0" in output
        assert "Unresolved: 0" in output

    def test_handles_unresolved_station_without_crashing_by_default(self) -> None:
        Station.objects.create(
            opis_id="301",
            name="Valid Station",
            city="Tulsa",
            state="OK",
            retail_price=Decimal("3.100"),
        )
        Station.objects.create(
            opis_id="302",
            name="Invalid Station",
            city="Ghost",
            state="XX",
            retail_price=Decimal("3.500"),
        )

        def side_effect(loc: str) -> Point:
            if "Ghost" in loc:
                raise GeocodingUnresolvedError("Unable to resolve")
            return Point(-95.9928, 36.1540, srid=4326)

        out = io.StringIO()
        with patch(
            "routing.services.GeocodingService.resolve_point",
            side_effect=side_effect,
        ):
            call_command("geocode_stations", stdout=out)

        valid_st = Station.objects.get(opis_id="301")
        invalid_st = Station.objects.get(opis_id="302")
        assert valid_st.location is not None
        assert invalid_st.location is None

        output = out.getvalue()
        assert "Total considered: 2" in output
        assert "Geocoded: 1" in output
        assert "Skipped: 0" in output
        assert "Unresolved: 1" in output

    def test_strict_flag_raises_command_error_on_unresolved(self) -> None:
        Station.objects.create(
            opis_id="401",
            name="Unresolvable Station",
            city="Ghost",
            state="XX",
            retail_price=Decimal("3.500"),
        )

        with (
            patch(
                "routing.services.GeocodingService.resolve_point",
                side_effect=GeocodingUnresolvedError("Unable to resolve"),
            ),
            pytest.raises(CommandError, match="Geocoding unresolved for Ghost, XX"),
        ):
            call_command("geocode_stations", "--strict")

    def test_all_flag_re_geocodes_existing_stations(self) -> None:
        Station.objects.create(
            opis_id="501",
            name="Station Already Geocoded",
            city="Tulsa",
            state="OK",
            retail_price=Decimal("3.100"),
            location=Point(-95.9928, 36.1540, srid=4326),
        )

        out = io.StringIO()
        with patch("routing.services.GeocodingService.resolve_point") as mock_resolve:
            mock_resolve.return_value = Point(-95.9928, 36.1540, srid=4326)
            call_command("geocode_stations", "--all", stdout=out)

            mock_resolve.assert_called_once_with("Tulsa, OK")

        output = out.getvalue()
        assert "Total considered: 1" in output
        assert "Geocoded: 1" in output
        assert "Skipped: 0" in output
        assert "Unresolved: 0" in output
