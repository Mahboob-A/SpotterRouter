from decimal import Decimal

import pytest
from django.contrib.gis.geos import Point

from stations.models import Station
from stations.repositories import StationRepository


@pytest.mark.django_db
class StationRepositoryTests:
    def test_get_by_opis_id_returns_matching_station(self) -> None:
        station = Station.objects.create(
            opis_id="1001",
            name="Pilot Test",
            city="Tulsa",
            state="OK",
            retail_price=Decimal("3.219"),
        )

        found = StationRepository().get_by_opis_id("1001")

        assert found == station

    def test_get_by_opis_id_returns_none_when_missing(self) -> None:
        found = StationRepository().get_by_opis_id("missing")

        assert found is None

    def test_needing_geocoding_returns_only_missing_locations(self) -> None:
        missing = Station.objects.create(
            opis_id="1001",
            name="Pilot Test",
            city="Tulsa",
            state="OK",
            retail_price=Decimal("3.219"),
        )
        Station.objects.create(
            opis_id="1002",
            name="Love Test",
            city="Dallas",
            state="TX",
            retail_price=Decimal("3.109"),
            location=Point(-96.7970, 32.7767, srid=4326),
        )

        stations = list(StationRepository().needing_geocoding())

        assert stations == [missing]
