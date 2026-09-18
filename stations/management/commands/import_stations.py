import csv
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from stations.models import RawStationImport


class Command(BaseCommand):
    help = "Import raw OPIS station rows into staging."

    required_columns = {
        "OPIS Truckstop ID",
        "Truckstop Name",
        "Address",
        "City",
        "State",
        "Rack ID",
        "Retail Price",
    }

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("csv_path", help="Path to the OPIS fuel-prices CSV file.")

    def handle(self, *args: Any, **options: Any) -> None:
        csv_path = Path(str(options["csv_path"]))
        if not csv_path.exists():
            raise CommandError(f"CSV file does not exist: {csv_path}")

        count = self._import_rows(csv_path)
        self.stdout.write(self.style.SUCCESS(f"Imported {count} raw station rows."))

    def _import_rows(self, csv_path: Path) -> int:
        with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            self._validate_headers(reader.fieldnames)
            rows = [
                self._build_raw_station(row, index)
                for index, row in enumerate(reader, 2)
            ]

        with transaction.atomic():
            RawStationImport.objects.bulk_create(rows, batch_size=1000)
        return len(rows)

    def _validate_headers(self, fieldnames: Sequence[str] | None) -> None:
        if fieldnames is None:
            raise CommandError("CSV file is missing a header row.")

        missing = self.required_columns.difference(fieldnames)
        if missing:
            column_list = ", ".join(sorted(missing))
            raise CommandError(f"CSV file is missing columns: {column_list}")

    def _build_raw_station(
        self,
        row: dict[str, str | None],
        row_number: int,
    ) -> RawStationImport:
        try:
            retail_price = Decimal(self._required(row, "Retail Price", row_number))
        except InvalidOperation as exc:
            message = f"Row {row_number} has an invalid retail price."
            raise CommandError(message) from exc

        return RawStationImport(
            opis_id=self._required(row, "OPIS Truckstop ID", row_number),
            name=self._required(row, "Truckstop Name", row_number),
            address=self._required(row, "Address", row_number),
            city=self._required(row, "City", row_number),
            state=self._required(row, "State", row_number).upper(),
            rack_id=self._required(row, "Rack ID", row_number),
            retail_price=retail_price,
        )

    def _required(
        self,
        row: dict[str, str | None],
        column: str,
        row_number: int,
    ) -> str:
        value = row.get(column)
        if value is None or value.strip() == "":
            raise CommandError(f"Row {row_number} is missing {column}.")
        return value.strip()
