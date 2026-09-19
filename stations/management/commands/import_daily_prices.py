from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from stations.repositories import PricingDatasetRepository
from stations.services import DatasetIngestionService


class Command(BaseCommand):
    help = "Import and manage daily fuel pricing datasets in the ./dataset directory."

    def __init__(
        self,
        ingestion_service: DatasetIngestionService | None = None,
        dataset_repo: PricingDatasetRepository | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._service = ingestion_service or DatasetIngestionService()
        self._datasets = dataset_repo or PricingDatasetRepository()

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "csv_path",
            nargs="?",
            default=None,
            help=(
                "Path to CSV dataset. If omitted, automatically selects "
                "the latest file in ./dataset/."
            ),
        )
        parser.add_argument(
            "--list",
            action="store_true",
            default=False,
            help="List CSV datasets in ./dataset/ with ingestion and active status.",
        )
        parser.add_argument(
            "--activate",
            dest="activate_version",
            default=None,
            help="Activate an existing registered dataset by its version code or ID.",
        )
        parser.add_argument(
            "--version-code",
            dest="version_code",
            default=None,
            help="Optional unique version code (e.g. OPIS-2026-09-20).",
        )
        parser.add_argument(
            "--description",
            dest="description",
            default="",
            help="Optional description or release notes for this pricing dataset.",
        )
        parser.add_argument(
            "--no-active",
            action="store_true",
            default=False,
            help="Do not set this dataset as active after ingestion.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["list"]:
            self._handle_list()
            return

        if options["activate_version"]:
            self._handle_activate(options["activate_version"])
            return

        target_path: Path | None = None
        if options["csv_path"]:
            target_path = Path(options["csv_path"])
            if not target_path.exists():
                raise CommandError(f"Specified CSV file does not exist: {target_path}")
        else:
            # Auto-detect latest or pending file from ./dataset/
            disk_files = self._service.scan_dataset_directory()
            if not disk_files:
                raise CommandError(
                    "No CSV files found in ./dataset/. "
                    "Specify a path or place a CSV into ./dataset/."
                )

            # Check for any uningested files first
            pending = [f for f in disk_files if not f.is_ingested]
            if pending:
                target_path = Path(pending[0].filepath)
                self.stdout.write(
                    f"Auto-selected uningested file: {target_path.name}"
                )
            else:
                target_path = Path(disk_files[0].filepath)
                self.stdout.write(
                    f"All files ingested. Re-evaluating: {target_path.name}"
                )

        set_active = not options["no_active"]
        version_code = options.get("version_code")
        description = options.get("description", "")

        try:
            dataset = self._service.ingest(
                file_source=target_path,
                filename=target_path.name,
                version_code=version_code,
                description=description,
                set_active=set_active,
            )
        except Exception as exc:
            raise CommandError(f"Failed to ingest dataset: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully ingested dataset '{dataset.version_code}' "
                f"({dataset.station_count} stations, "
                f"min=${dataset.min_price}, max=${dataset.max_price}). "
                f"Active: {dataset.is_active}"
            )
        )

    def _handle_list(self) -> None:
        files = self._service.scan_dataset_directory()
        if not files:
            self.stdout.write("No CSV dataset files found in ./dataset/ directory.")
            return

        self.stdout.write("\nFiles in ./dataset/ Directory:")
        header_fmt = "{:<32} {:<10} {:<16} {:<18} {:<8}"
        self.stdout.write(
            header_fmt.format("Filename", "Size", "Status", "Version Code", "Active")
        )
        self.stdout.write("-" * 88)

        for f in files:
            if f.is_active:
                status_str = "Active"
                active_str = "[ACTIVE]"
            elif f.is_ingested:
                status_str = "Ingested"
                active_str = "No"
            else:
                status_str = "Pending Ingest"
                active_str = "No"

            ver = f.version_code or "-"
            self.stdout.write(
                header_fmt.format(
                    f.filename[:30], f.size_display, status_str, ver[:16], active_str
                )
            )
        self.stdout.write("")

    def _handle_activate(self, version_or_id: str) -> None:
        dataset = self._datasets.get_by_version_code(version_or_id)
        if not dataset:
            # Try by UUID
            try:
                import uuid

                u = uuid.UUID(version_or_id)
                dataset = self._datasets.get_by_id(u)
            except (ValueError, Exception):
                dataset = None

        if not dataset:
            raise CommandError(f"No dataset found matching '{version_or_id}'.")

        activated = self._service.activate_dataset(str(dataset.id))
        self.stdout.write(
            self.style.SUCCESS(
                f"Activated dataset '{activated.version_code}' "
                f"({activated.station_count} stations)."
            )
        )
