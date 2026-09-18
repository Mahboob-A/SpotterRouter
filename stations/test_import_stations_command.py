from decimal import Decimal

import pytest
from django.core.management import CommandError, call_command

from stations.models import RawStationImport


@pytest.mark.django_db
class TestImportStationsCommand:
    def test_imports_raw_rows_and_preserves_duplicate_opis_ids(self, tmp_path) -> None:
        csv_path = tmp_path / "stations.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price",
                    "1001,Pilot Test,I-44 EXIT 1,Tulsa,OK,R-1,3.219",
                    "1001,Pilot Test,I-44 EXIT 1,Tulsa,OK,R-1,3.199",
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

    def test_invalid_rows_raise_command_error(self, tmp_path) -> None:
        csv_path = tmp_path / "stations.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price",
                    "1001,Pilot Test,I-44 EXIT 1,Tulsa,OK,R-1,not-a-price",
                ]
            ),
            encoding="utf-8",
        )

        with pytest.raises(CommandError):
            call_command("import_stations", str(csv_path))
