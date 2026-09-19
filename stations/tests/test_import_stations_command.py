import io
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from stations.models import RawStationImport

CSV_HEADER = ",".join(
    [
        "OPIS Truckstop ID",
        "Truckstop Name",
        "Address",
        "City",
        "State",
        "Rack ID",
        "Retail Price",
    ]
)


@pytest.mark.django_db
class TestImportStationsCommand:
    def test_imports_raw_rows_and_preserves_duplicate_opis_ids(
        self,
        tmp_path: Path,
    ) -> None:
        csv_path = tmp_path / "stations.csv"
        csv_path.write_text(
            "\n".join(
                [
                    CSV_HEADER,
                    "1001,Pilot Test,I-44 EXIT 1,Tulsa,ok,R-1,3.219",
                    "1001,Pilot Test,I-44 EXIT 1,Tulsa,ok,R-1,3.199",
                ]
            ),
            encoding="utf-8",
        )

        call_command("import_stations", str(csv_path))

        rows = list(RawStationImport.objects.order_by("retail_price"))
        assert len(rows) == 2
        assert {row.opis_id for row in rows} == {"1001"}
        assert rows[0].retail_price == Decimal("3.199")
        assert rows[1].retail_price == Decimal("3.219")
        assert rows[0].state == "OK"
        assert rows[1].state == "OK"

    def test_invalid_price_raises_command_error(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "stations.csv"
        csv_path.write_text(
            "\n".join(
                [
                    CSV_HEADER,
                    "1001,Pilot Test,I-44 EXIT 1,Tulsa,OK,R-1,not-a-price",
                ]
            ),
            encoding="utf-8",
        )

        with pytest.raises(CommandError, match="invalid retail price"):
            call_command("import_stations", str(csv_path))

    def test_missing_file_raises_command_error(self, tmp_path: Path) -> None:
        missing_path = tmp_path / "nonexistent.csv"

        with pytest.raises(CommandError, match="CSV file does not exist"):
            call_command("import_stations", str(missing_path))

    def test_missing_header_raises_command_error(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("", encoding="utf-8")

        with pytest.raises(CommandError, match="missing a header row"):
            call_command("import_stations", str(csv_path))

    def test_missing_columns_raise_command_error(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "stations.csv"
        csv_path.write_text(
            "OPIS Truckstop ID,Truckstop Name,Address\n1001,Pilot Test,I-44 EXIT 1\n",
            encoding="utf-8",
        )

        with pytest.raises(CommandError, match="CSV file is missing columns"):
            call_command("import_stations", str(csv_path))

    def test_missing_field_value_raises_command_error(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "stations.csv"
        csv_path.write_text(
            "\n".join(
                [
                    CSV_HEADER,
                    "1001,,I-44 EXIT 1,Tulsa,OK,R-1,3.199",
                ]
            ),
            encoding="utf-8",
        )

        with pytest.raises(CommandError, match="is missing Truckstop Name"):
            call_command("import_stations", str(csv_path))

    def test_command_prints_count_summary(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "stations.csv"
        csv_path.write_text(
            "\n".join(
                [
                    CSV_HEADER,
                    "1001,Pilot Test,I-44 EXIT 1,Tulsa,OK,R-1,3.219",
                    "1002,Love's Test,I-40 EXIT 2,Oklahoma City,OK,R-2,3.149",
                ]
            ),
            encoding="utf-8",
        )

        out = io.StringIO()
        call_command("import_stations", str(csv_path), stdout=out)

        assert "Imported 2 raw station rows." in out.getvalue()
