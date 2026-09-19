import io
from pathlib import Path
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from stations.models import PricingDataset
from stations.tests.test_dataset_service import SAMPLE_CSV, SAMPLE_CSV_UPDATED


@pytest.mark.django_db
class TestImportDailyPricesCommand:
    def test_list_command_outputs_status(
        self, tmp_path: Path, settings: Any
    ) -> None:
        settings.DATASET_DIR = tmp_path
        (tmp_path / "pending_data.csv").write_text(SAMPLE_CSV)

        out = io.StringIO()
        call_command("import_daily_prices", "--list", stdout=out)
        output = out.getvalue()

        assert "Files in ./dataset/ Directory:" in output
        assert "pending_data.csv" in output
        assert "Pending Ingest" in output

    def test_import_with_explicit_path(
        self, tmp_path: Path, settings: Any
    ) -> None:
        settings.DATASET_DIR = tmp_path
        csv_file = tmp_path / "test_import.csv"
        csv_file.write_text(SAMPLE_CSV)

        out = io.StringIO()
        call_command(
            "import_daily_prices",
            str(csv_file),
            "--version-code=TEST-CMD-V1",
            "--description=Test import command",
            stdout=out,
        )
        output = out.getvalue()

        assert "Successfully ingested dataset 'TEST-CMD-V1'" in output
        ds = PricingDataset.objects.get(version_code="TEST-CMD-V1")
        assert ds.is_active is True
        assert ds.station_count == 3

    def test_import_auto_detects_pending_file(
        self, tmp_path: Path, settings: Any
    ) -> None:
        settings.DATASET_DIR = tmp_path
        (tmp_path / "morning_prices.csv").write_text(SAMPLE_CSV)

        out = io.StringIO()
        call_command("import_daily_prices", stdout=out)
        output = out.getvalue()

        assert "Auto-selected uningested file: morning_prices.csv" in output
        assert "Successfully ingested dataset" in output

    def test_activate_option_switches_active_dataset(
        self, tmp_path: Path, settings: Any
    ) -> None:
        settings.DATASET_DIR = tmp_path
        f1 = tmp_path / "p1.csv"
        f1.write_text(SAMPLE_CSV)
        f2 = tmp_path / "p2.csv"
        f2.write_text(SAMPLE_CSV_UPDATED)

        call_command("import_daily_prices", str(f1), "--version-code=ACT-CMD-1")
        call_command("import_daily_prices", str(f2), "--version-code=ACT-CMD-2")

        d1 = PricingDataset.objects.get(version_code="ACT-CMD-1")
        d2 = PricingDataset.objects.get(version_code="ACT-CMD-2")
        assert d2.is_active is True
        assert d1.is_active is False

        out = io.StringIO()
        call_command("import_daily_prices", "--activate=ACT-CMD-1", stdout=out)
        assert "Activated dataset 'ACT-CMD-1'" in out.getvalue()

        d1.refresh_from_db()
        d2.refresh_from_db()
        assert d1.is_active is True
        assert d2.is_active is False

    def test_missing_file_raises_command_error(
        self, tmp_path: Path, settings: Any
    ) -> None:
        settings.DATASET_DIR = tmp_path
        with pytest.raises(CommandError, match="Specified CSV file does not exist"):
            call_command("import_daily_prices", "/non/existent/path.csv")
