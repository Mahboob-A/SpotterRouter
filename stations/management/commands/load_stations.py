from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from stations.models import RawStationImport, Station
from stations.repositories import StationRepository


class Command(BaseCommand):
    help = "Deduplicate staging station rows into the Station table by min price."

    def __init__(
        self,
        *args: Any,
        station_repository: StationRepository | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._stations = station_repository or StationRepository()

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--override",
            action="store_true",
            help="Clear and reload stations if station records already exist.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        override: bool = options.get("override", False)

        if self._stations.exists() and not override:
            raise CommandError(
                "Station records already exist. Pass --override to reload."
            )

        with transaction.atomic():
            if override:
                self._stations.clear_all()

            deduped_rows = RawStationImport.objects.order_by(
                "opis_id", "retail_price", "id"
            ).distinct("opis_id")

            stations_to_create = [
                Station(
                    opis_id=row.opis_id,
                    name=row.name,
                    city=row.city,
                    state=row.state,
                    retail_price=row.retail_price,
                )
                for row in deduped_rows
            ]

            created = self._stations.bulk_create(
                stations_to_create,
                batch_size=1000,
            )

        self.stdout.write(
            self.style.SUCCESS(f"Loaded {len(created)} unique stations.")
        )
