import csv
import hashlib
import io
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, BinaryIO, TextIO

from django.conf import settings
from django.db import transaction

from routing.adapters.local_geocoder import LocalGeocoder
from stations.models import PricingDataset, Station, StationPrice
from stations.repositories import PricingDatasetRepository, StationRepository

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "OPIS Truckstop ID",
    "Truckstop Name",
    "Address",
    "City",
    "State",
    "Rack ID",
    "Retail Price",
}


@dataclass(frozen=True)
class DiskDatasetInfo:
    """Metadata describing a CSV dataset file found on the local filesystem."""

    filename: str
    filepath: str
    size_bytes: int
    size_display: str
    modified_at: datetime
    file_hash: str
    is_ingested: bool
    is_active: bool
    version_code: str | None = None
    station_count: int | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None


class DatasetIngestionService:
    """Service orchestrating fuel dataset ingestion, disk scanning, and activation."""

    def __init__(
        self,
        dataset_repo: PricingDatasetRepository | None = None,
        station_repo: StationRepository | None = None,
        geocoder: LocalGeocoder | None = None,
    ) -> None:
        self._datasets = dataset_repo or PricingDatasetRepository()
        self._stations = station_repo or StationRepository()
        self._geocoder = geocoder or LocalGeocoder()

    def get_dataset_directory(self) -> Path:
        """Return the resolved Path to the ./dataset directory, ensuring it exists."""
        base_dir = Path(settings.BASE_DIR)
        dir_path = getattr(settings, "DATASET_DIR", base_dir / "dataset")
        dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def scan_dataset_directory(
        self, directory_path: Path | None = None
    ) -> list[DiskDatasetInfo]:
        """Scan dataset directory and correlate CSV files with database registry."""
        target_dir = directory_path or self.get_dataset_directory()
        if not target_dir.exists() or not target_dir.is_dir():
            return []

        all_registered = {ds.file_hash: ds for ds in self._datasets.list_all()}
        results: list[DiskDatasetInfo] = []

        csv_files = sorted(
            target_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        for path in csv_files:
            try:
                stat = path.stat()
                with path.open("rb") as f:
                    file_bytes = f.read()
                file_hash = hashlib.sha256(file_bytes).hexdigest()

                size_bytes = stat.st_size
                if size_bytes < 1024:
                    size_display = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_display = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_display = f"{size_bytes / (1024 * 1024):.1f} MB"

                mod_time = datetime.fromtimestamp(stat.st_mtime)
                reg_ds = all_registered.get(file_hash)

                if reg_ds:
                    results.append(
                        DiskDatasetInfo(
                            filename=path.name,
                            filepath=str(path),
                            size_bytes=size_bytes,
                            size_display=size_display,
                            modified_at=mod_time,
                            file_hash=file_hash,
                            is_ingested=True,
                            is_active=reg_ds.is_active,
                            version_code=reg_ds.version_code,
                            station_count=reg_ds.station_count,
                            min_price=reg_ds.min_price,
                            max_price=reg_ds.max_price,
                        )
                    )
                else:
                    results.append(
                        DiskDatasetInfo(
                            filename=path.name,
                            filepath=str(path),
                            size_bytes=size_bytes,
                            size_display=size_display,
                            modified_at=mod_time,
                            file_hash=file_hash,
                            is_ingested=False,
                            is_active=False,
                        )
                    )
            except Exception as exc:
                logger.warning("Error reading dataset file %s: %s", path, exc)

        return results

    def ingest(
        self,
        file_source: Path | str | BinaryIO | TextIO | bytes,
        filename: str,
        version_code: str | None = None,
        description: str = "",
        set_active: bool = True,
    ) -> PricingDataset:
        """Parse, validate, and atomically ingest a CSV dataset into the system."""
        file_bytes: bytes
        target_dir = self.get_dataset_directory()

        if isinstance(file_source, (str, Path)):
            src_path = Path(file_source)
            if not src_path.exists():
                raise FileNotFoundError(f"CSV file not found: {src_path}")
            with src_path.open("rb") as f:
                file_bytes = f.read()
            # If outside target dataset dir, save a copy into ./dataset/
            dest_path = target_dir / src_path.name
            if src_path.resolve() != dest_path.resolve():
                dest_path.write_bytes(file_bytes)
        elif isinstance(file_source, bytes):
            file_bytes = file_source
            dest_path = target_dir / filename
            dest_path.write_bytes(file_bytes)
        elif hasattr(file_source, "read"):
            content = file_source.read()
            if isinstance(content, str):
                file_bytes = content.encode("utf-8")
            else:
                file_bytes = content
            dest_path = target_dir / filename
            dest_path.write_bytes(file_bytes)
        else:
            raise ValueError(f"Unsupported file source type: {type(file_source)}")

        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Check if identical content is already ingested
        existing_ds = self._datasets.get_by_file_hash(file_hash)
        if existing_ds is not None:
            if set_active and not existing_ds.is_active:
                return self.activate_dataset(str(existing_ds.id))
            return existing_ds

        # Decode content for CSV DictReader
        try:
            text_stream = io.StringIO(file_bytes.decode("utf-8-sig"))
        except UnicodeDecodeError:
            text_stream = io.StringIO(file_bytes.decode("latin-1"))

        reader = csv.DictReader(text_stream)
        if not reader.fieldnames:
            raise ValueError("CSV dataset is empty or missing a header row.")

        fieldnames_set = set(reader.fieldnames)
        missing_cols = REQUIRED_COLUMNS.difference(fieldnames_set)
        if missing_cols:
            raise ValueError(
                f"CSV is missing required columns: {', '.join(sorted(missing_cols))}"
            )

        # Deduplicate rows by opis_id, choosing lowest retail price
        deduped_rows: dict[str, dict[str, Any]] = {}
        for _row_num, row in enumerate(reader, start=2):
            opis_id = (row.get("OPIS Truckstop ID") or "").strip()
            if not opis_id:
                continue

            price_raw = (row.get("Retail Price") or "").strip()
            try:
                price = Decimal(price_raw)
            except (InvalidOperation, ValueError):
                continue

            name = (row.get("Truckstop Name") or "").strip()
            address = (row.get("Address") or "").strip()
            city = (row.get("City") or "").strip()
            state = (row.get("State") or "").strip().upper()

            if (
                opis_id not in deduped_rows
                or price < deduped_rows[opis_id]["retail_price"]
            ):
                deduped_rows[opis_id] = {
                    "opis_id": opis_id,
                    "name": name,
                    "address": address,
                    "city": city,
                    "state": state,
                    "retail_price": price,
                }

        if not deduped_rows:
            raise ValueError("No valid station rows found in CSV dataset.")

        # Determine version code
        resolved_version_code = self._resolve_version_code(version_code, filename)

        with transaction.atomic():
            if set_active:
                PricingDataset.objects.filter(is_active=True).update(is_active=False)

            dataset = PricingDataset.objects.create(
                version_code=resolved_version_code,
                filename=filename,
                file_hash=file_hash,
                is_active=set_active,
                description=description,
            )

            # Separate into existing stations to update and new stations to create
            existing_stations_map = {
                s.opis_id: s
                for s in Station.objects.filter(opis_id__in=deduped_rows.keys())
            }

            stations_to_update: list[Station] = []
            stations_to_create: list[Station] = []

            for opis_id, data in deduped_rows.items():
                if opis_id in existing_stations_map:
                    st = existing_stations_map[opis_id]
                    if set_active:
                        st.retail_price = data["retail_price"]
                        stations_to_update.append(st)
                else:
                    # Resolve coordinates for new station
                    point = None
                    try:
                        coords = self._geocoder.resolve(
                            f"{data['city']}, {data['state']}"
                        )
                        if coords:
                            point = coords.to_point()
                    except Exception:
                        pass

                    new_st = Station(
                        opis_id=opis_id,
                        name=data["name"],
                        city=data["city"],
                        state=data["state"],
                        retail_price=data["retail_price"],
                        location=point,
                    )
                    stations_to_create.append(new_st)

            if set_active and stations_to_update:
                Station.objects.bulk_update(
                    stations_to_update, fields=["retail_price"], batch_size=1000
                )

            if stations_to_create:
                Station.objects.bulk_create(stations_to_create, batch_size=1000)

            # Re-fetch all IDs to link StationPrice rows
            all_stations_id_map = dict(
                Station.objects.filter(opis_id__in=deduped_rows.keys()).values_list(
                    "opis_id", "id"
                )
            )

            station_prices = [
                StationPrice(
                    dataset=dataset,
                    station_id=all_stations_id_map[opis_id],
                    retail_price=data["retail_price"],
                )
                for opis_id, data in deduped_rows.items()
                if opis_id in all_stations_id_map
            ]
            StationPrice.objects.bulk_create(station_prices, batch_size=1000)

            prices = [d["retail_price"] for d in deduped_rows.values()]
            dataset.station_count = len(station_prices)
            dataset.min_price = min(prices) if prices else Decimal("0.000")
            dataset.max_price = max(prices) if prices else Decimal("0.000")
            dataset.save(update_fields=["station_count", "min_price", "max_price"])

        logger.info(
            "Ingested dataset '%s': %d stations, active=%s",
            dataset.version_code,
            dataset.station_count,
            dataset.is_active,
        )
        return dataset

    def activate_dataset(self, dataset_id: str) -> PricingDataset:
        """Set dataset active and synchronize Station.retail_price to its prices."""
        with transaction.atomic():
            PricingDataset.objects.filter(is_active=True).update(is_active=False)
            dataset = PricingDataset.objects.get(id=dataset_id)
            dataset.is_active = True
            dataset.save(update_fields=["is_active"])

            # Sync active Station retail_price to this dataset's snapshots
            station_price_map = dict(
                StationPrice.objects.filter(dataset=dataset).values_list(
                    "station_id", "retail_price"
                )
            )

            stations = list(Station.objects.filter(id__in=station_price_map.keys()))
            for st in stations:
                st.retail_price = station_price_map[st.id]

            Station.objects.bulk_update(
                stations, fields=["retail_price"], batch_size=1000
            )

        logger.info(
            "Activated dataset '%s' across %d stations.",
            dataset.version_code,
            len(stations),
        )
        return dataset

    def _resolve_version_code(self, version_code: str | None, filename: str) -> str:
        """Resolve a unique, formatted version code from input or filename."""
        if version_code and version_code.strip():
            candidate = version_code.strip()
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
            candidate = f"OPIS-{date_str}"

        # Ensure uniqueness
        if not PricingDataset.objects.filter(version_code=candidate).exists():
            return candidate

        timestamp_suffix = datetime.now().strftime("%H%M%S")
        candidate_with_time = f"{candidate}-{timestamp_suffix}"
        if not PricingDataset.objects.filter(version_code=candidate_with_time).exists():
            return candidate_with_time

        return f"{candidate}-{uuid.uuid4().hex[:6]}"
