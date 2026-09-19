import io
from decimal import Decimal

import pytest
from django.core.management import CommandError, call_command

from stations.models import RawStationImport, Station


@pytest.mark.django_db
class TestLoadStationsCommand:
    def test_deduplicates_by_min_retail_price_per_opis_id(self) -> None:
        RawStationImport.objects.create(
            opis_id="1001",
            name="Station A",
            address="Exit 1",
            city="Tulsa",
            state="OK",
            rack_id="R1",
            retail_price=Decimal("3.500"),
        )
        RawStationImport.objects.create(
            opis_id="1001",
            name="Station A",
            address="Exit 1",
            city="Tulsa",
            state="OK",
            rack_id="R1",
            retail_price=Decimal("3.100"),
        )
        RawStationImport.objects.create(
            opis_id="1001",
            name="Station A",
            address="Exit 1",
            city="Tulsa",
            state="OK",
            rack_id="R1",
            retail_price=Decimal("3.400"),
        )
        RawStationImport.objects.create(
            opis_id="1002",
            name="Station B",
            address="Exit 2",
            city="Oklahoma City",
            state="OK",
            rack_id="R2",
            retail_price=Decimal("2.990"),
        )
        RawStationImport.objects.create(
            opis_id="1002",
            name="Station B",
            address="Exit 2",
            city="Oklahoma City",
            state="OK",
            rack_id="R2",
            retail_price=Decimal("3.050"),
        )

        call_command("load_stations")

        stations = list(Station.objects.order_by("opis_id"))
        assert len(stations) == 2
        assert stations[0].opis_id == "1001"
        assert stations[0].retail_price == Decimal("3.100")
        assert stations[0].city == "Tulsa"
        assert stations[1].opis_id == "1002"
        assert stations[1].retail_price == Decimal("2.990")
        assert stations[1].city == "Oklahoma City"

    def test_refuses_to_run_when_stations_already_exist_without_override(
        self,
    ) -> None:
        Station.objects.create(
            opis_id="9999",
            name="Existing Station",
            city="Dallas",
            state="TX",
            retail_price=Decimal("3.000"),
        )

        with pytest.raises(CommandError, match="already exist"):
            call_command("load_stations")

    def test_runs_when_override_specified(self) -> None:
        Station.objects.create(
            opis_id="9999",
            name="Existing Station",
            city="Dallas",
            state="TX",
            retail_price=Decimal("3.000"),
        )
        RawStationImport.objects.create(
            opis_id="1001",
            name="New Station",
            address="Exit 1",
            city="Tulsa",
            state="OK",
            rack_id="R1",
            retail_price=Decimal("3.200"),
        )

        call_command("load_stations", "--override")

        stations = list(Station.objects.all())
        assert len(stations) == 1
        assert stations[0].opis_id == "1001"
        assert stations[0].retail_price == Decimal("3.200")

    def test_command_prints_count_summary(self) -> None:
        RawStationImport.objects.create(
            opis_id="1001",
            name="Station A",
            address="Exit 1",
            city="Tulsa",
            state="OK",
            rack_id="R1",
            retail_price=Decimal("3.200"),
        )

        out = io.StringIO()
        call_command("load_stations", stdout=out)

        assert "Loaded 1 unique stations." in out.getvalue()
