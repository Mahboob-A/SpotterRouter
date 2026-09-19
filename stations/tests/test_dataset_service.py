from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from stations.models import Station, StationPrice
from stations.services import DatasetIngestionService

CSV_HEADER = (
    "OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price\n"
)
SAMPLE_CSV = CSV_HEADER + (
    "1001,Pilot Travel Center,123 Main St,Tulsa,OK,1,3.459\n"
    "1002,Love's Travel Stop,456 Oak St,Dallas,TX,1,3.199\n"
    "1003,TA Express,789 Pine St,Little Rock,AR,1,3.299\n"
)

SAMPLE_CSV_UPDATED = CSV_HEADER + (
    "1001,Pilot Travel Center,123 Main St,Tulsa,OK,1,3.699\n"
    "1002,Love's Travel Stop,456 Oak St,Dallas,TX,1,3.099\n"
    "1004,Flying J,999 Elm St,Memphis,TN,1,3.159\n"
)


@pytest.mark.django_db
class TestDatasetIngestionService:
    def test_get_dataset_directory_creates_dir(
        self, tmp_path: Path, settings: Any
    ) -> None:
        target = tmp_path / "custom_dataset"
        settings.DATASET_DIR = target
        service = DatasetIngestionService()

        resolved = service.get_dataset_directory()

        assert resolved.exists()
        assert resolved == target

    def test_scan_dataset_directory(self, tmp_path: Path, settings: Any) -> None:
        settings.DATASET_DIR = tmp_path
        service = DatasetIngestionService()

        # Place a CSV file on disk
        csv_file = tmp_path / "test_prices.csv"
        csv_file.write_text(SAMPLE_CSV)

        # Before ingestion, scan sees it as pending
        scanned = service.scan_dataset_directory(tmp_path)
        assert len(scanned) == 1
        info = scanned[0]
        assert info.filename == "test_prices.csv"
        assert info.is_ingested is False
        assert info.is_active is False

        # Ingest it
        _ = service.ingest(
            file_source=csv_file,
            filename="test_prices.csv",
            version_code="TEST-SCAN-1",
            set_active=True,
        )

        # Now scan sees it as ingested and active
        scanned_after = service.scan_dataset_directory(tmp_path)
        assert len(scanned_after) == 1
        assert scanned_after[0].is_ingested is True
        assert scanned_after[0].is_active is True
        assert scanned_after[0].version_code == "TEST-SCAN-1"
        assert scanned_after[0].station_count == 3

    def test_ingest_creates_stations_and_dataset(
        self, tmp_path: Path, settings: Any
    ) -> None:
        settings.DATASET_DIR = tmp_path
        mock_geocoder = MagicMock()
        mock_geocoder.resolve.return_value = None
        service = DatasetIngestionService(geocoder=mock_geocoder)

        ds = service.ingest(
            file_source=SAMPLE_CSV.encode("utf-8"),
            filename="daily_2026.csv",
            version_code="DAILY-V1",
            description="Test daily import",
            set_active=True,
        )

        assert ds.version_code == "DAILY-V1"
        assert ds.station_count == 3
        assert ds.min_price == Decimal("3.199")
        assert ds.max_price == Decimal("3.459")
        assert ds.is_active is True

        # Check stations were created
        assert Station.objects.filter(opis_id="1001").exists()
        assert Station.objects.filter(opis_id="1002").exists()
        assert StationPrice.objects.filter(dataset=ds).count() == 3

    def test_ingest_updates_existing_stations_and_handles_duplicate(
        self, tmp_path: Path, settings: Any
    ) -> None:
        settings.DATASET_DIR = tmp_path
        mock_geocoder = MagicMock()
        mock_geocoder.resolve.return_value = None
        service = DatasetIngestionService(geocoder=mock_geocoder)

        ds1 = service.ingest(
            file_source=SAMPLE_CSV.encode("utf-8"),
            filename="v1.csv",
            version_code="VER-1",
            set_active=True,
        )
        assert Station.objects.get(opis_id="1001").retail_price == Decimal("3.459")

        # Ingest updated dataset
        ds2 = service.ingest(
            file_source=SAMPLE_CSV_UPDATED.encode("utf-8"),
            filename="v2.csv",
            version_code="VER-2",
            set_active=True,
        )
        assert ds2.version_code == "VER-2"
        assert ds2.is_active is True
        ds1.refresh_from_db()
        assert ds1.is_active is False

        # Station 1001 price updated to new dataset
        assert Station.objects.get(opis_id="1001").retail_price == Decimal("3.699")
        # Station 1004 created
        assert Station.objects.filter(opis_id="1004").exists()

        # Ingesting the same content again returns existing dataset
        ds2_dup = service.ingest(
            file_source=SAMPLE_CSV_UPDATED.encode("utf-8"),
            filename="v2_dup.csv",
            version_code="VER-2-DUP",
            set_active=True,
        )
        assert ds2_dup.id == ds2.id

    def test_ingest_missing_columns_raises_error(
        self, tmp_path: Path, settings: Any
    ) -> None:
        settings.DATASET_DIR = tmp_path
        service = DatasetIngestionService()
        invalid_csv = "Invalid,Header,Only\n1,2,3"

        with pytest.raises(ValueError, match="CSV is missing required column"):
            service.ingest(
                file_source=invalid_csv.encode("utf-8"),
                filename="invalid.csv",
                version_code="BAD-CSV",
            )

    def test_activate_dataset_switches_active_and_prices(
        self, tmp_path: Path, settings: Any
    ) -> None:
        settings.DATASET_DIR = tmp_path
        mock_geocoder = MagicMock()
        mock_geocoder.resolve.return_value = None
        service = DatasetIngestionService(geocoder=mock_geocoder)

        ds1 = service.ingest(
            file_source=SAMPLE_CSV.encode("utf-8"),
            filename="ds1.csv",
            version_code="ACT-1",
            set_active=True,
        )
        ds2 = service.ingest(
            file_source=SAMPLE_CSV_UPDATED.encode("utf-8"),
            filename="ds2.csv",
            version_code="ACT-2",
            set_active=True,
        )

        assert Station.objects.get(opis_id="1001").retail_price == Decimal("3.699")

        # Reactivate ds1
        service.activate_dataset(str(ds1.id))
        ds1.refresh_from_db()
        ds2.refresh_from_db()
        assert ds1.is_active is True
        assert ds2.is_active is False
        assert Station.objects.get(opis_id="1001").retail_price == Decimal("3.459")
