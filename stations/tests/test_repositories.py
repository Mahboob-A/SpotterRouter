from decimal import Decimal

import pytest
from django.contrib.gis.geos import Point

from stations.models import Station
from stations.repositories import StationRepository


@pytest.mark.django_db
class TestStationRepository:
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


@pytest.mark.django_db
class TestPricingDatasetRepository:
    def test_pricing_dataset_repository_queries(self) -> None:
        from stations.models import PricingDataset
        from stations.repositories import PricingDatasetRepository

        repo = PricingDatasetRepository()
        PricingDataset.objects.all().delete()

        d1 = PricingDataset.objects.create(
            version_code="DATASET-A",
            filename="dataset_a.csv",
            file_hash="hash_a",
            station_count=10,
            is_active=False,
        )
        d2 = PricingDataset.objects.create(
            version_code="DATASET-B",
            filename="dataset_b.csv",
            file_hash="hash_b",
            station_count=20,
            is_active=True,
        )

        assert repo.get_active() == d2
        assert repo.get_by_version_code("DATASET-A") == d1
        assert repo.get_by_file_hash("hash_b") == d2
        assert repo.get_by_version_code("UNKNOWN") is None
        assert list(repo.list_all()) == [d2, d1]

        # Test set_active
        activated = repo.set_active(str(d1.id))
        assert activated.id == d1.id
        assert activated.is_active is True
        d2.refresh_from_db()
        assert d2.is_active is False
