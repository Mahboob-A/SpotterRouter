import logging
from typing import Any

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from core.exceptions import GeocodingUnresolvedError
from routing.services import GeocodingService
from stations.models import Station
from stations.repositories import StationRepository

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Geocode station city and state into SRID 4326 Point locations."

    def __init__(
        self,
        station_repo: StationRepository | None = None,
        geocoding_service: GeocodingService | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.station_repo = station_repo or StationRepository()
        self.geocoding_service = geocoding_service or GeocodingService()

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for bulk updates (default: 500).",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            default=False,
            help="Raise CommandError immediately if any station cannot be geocoded.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            default=False,
            help="Re-geocode all stations even if location is already set.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of stations to process in this run.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        batch_size: int = options["batch_size"]
        strict: bool = options["strict"]
        re_geocode_all: bool = options["all"]
        limit: int | None = options.get("limit")

        if re_geocode_all:
            qs = self.station_repo.model.objects.all().order_by("opis_id")
            skipped = 0
        else:
            qs = self.station_repo.needing_geocoding()
            skipped = self.station_repo.model.objects.filter(
                location__isnull=False
            ).count()

        if limit is not None:
            stations_to_process = list(qs[:limit])
        else:
            stations_to_process = list(qs.iterator(chunk_size=batch_size))

        geocoded = 0
        unresolved = 0
        city_cache: dict[str, Point | None] = {}
        stations_to_update: list[Station] = []

        for station in stations_to_process:
            location_key = f"{station.city}, {station.state}"

            if location_key in city_cache:
                point = city_cache[location_key]
                if point is None:
                    if strict:
                        raise CommandError(f"Geocoding unresolved for {location_key}")
                    unresolved += 1
                    continue
            else:
                try:
                    point = self.geocoding_service.resolve_point(location_key)
                    city_cache[location_key] = point
                except GeocodingUnresolvedError as err:
                    city_cache[location_key] = None
                    logger.warning(
                        "Could not resolve geocoding for station opis_id=%s (%s): %s",
                        station.opis_id,
                        location_key,
                        err,
                    )
                    if strict:
                        msg = f"Geocoding unresolved for {location_key}"
                        raise CommandError(msg) from err
                    unresolved += 1
                    continue

            station.location = point
            stations_to_update.append(station)
            geocoded += 1

            if len(stations_to_update) >= batch_size:
                with transaction.atomic():
                    self.station_repo.bulk_update_locations(
                        stations_to_update,
                        batch_size=batch_size,
                    )
                stations_to_update.clear()

        if stations_to_update:
            with transaction.atomic():
                self.station_repo.bulk_update_locations(
                    stations_to_update,
                    batch_size=batch_size,
                )
            stations_to_update.clear()

        total_considered = skipped + geocoded + unresolved
        self.stdout.write(
            f"Geocoding complete: Total considered: {total_considered} | "
            f"Geocoded: {geocoded} | Skipped: {skipped} | Unresolved: {unresolved}."
        )
