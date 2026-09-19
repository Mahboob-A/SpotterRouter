import json
import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Min, Q
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views import View

from core.constants import CONTIGUOUS_48_STATES
from core.exceptions import FuelRouterError
from stations.models import Station
from stations.repositories import PricingDatasetRepository
from stations.services import DatasetIngestionService
from trips.reports import TripPdfReportService
from trips.repositories import TripPlanRepository
from trips.services import TripPlanningService
from ui.constants import PRESET_TRIP_PAIRS
from ui.docs_service import DocsService


class HomeView(View):
    """Presentation view for route planning input, presets, and recent trips."""

    def __init__(
        self,
        service: TripPlanningService | None = None,
        repository: TripPlanRepository | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._service = service or TripPlanningService()
        self._repository = repository or TripPlanRepository()

    def get(self, request: HttpRequest) -> HttpResponse:
        start = request.GET.get("start", "").strip()
        end = request.GET.get("end", "").strip()
        limit = 10
        recent_trips = self._repository.list_recent(limit=limit, offset=0)
        total_trips = self._repository.count_total()
        context = {
            "recent_trips": recent_trips,
            "presets": PRESET_TRIP_PAIRS,
            "start": start,
            "end": end,
            "has_more": total_trips > limit,
            "total_trips": total_trips,
        }
        return render(request, "ui/home.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        start = request.POST.get("start", "").strip()
        end = request.POST.get("end", "").strip()
        limit = 10
        recent_trips = self._repository.list_recent(limit=limit, offset=0)
        total_trips = self._repository.count_total()

        if not start or not end:
            context = {
                "recent_trips": recent_trips,
                "presets": PRESET_TRIP_PAIRS,
                "start": start,
                "end": end,
                "has_more": total_trips > limit,
                "total_trips": total_trips,
                "error": "Both start and destination locations are required.",
            }
            return render(request, "ui/home.html", context, status=400)

        force_refresh = request.POST.get("force_refresh") in ("1", "true", "True", "on")
        try:
            plan = self._service.plan_trip(
                start_input=start,
                end_input=end,
                force_refresh=force_refresh,
            )
            cache_status = "HIT" if plan.is_cache_hit else "MISS"
            request.session[f"trip_cache_{plan.id}"] = cache_status
            response = redirect("trip-detail", trip_id=plan.id)
            response["X-Cache"] = cache_status
            return response
        except FuelRouterError as exc:
            context = {
                "recent_trips": recent_trips,
                "presets": PRESET_TRIP_PAIRS,
                "start": start,
                "end": end,
                "has_more": total_trips > limit,
                "total_trips": total_trips,
                "error": str(exc),
            }
            return render(request, "ui/home.html", context, status=400)


class RecentTripsApiView(View):
    """JSON API endpoint for loading paginated recent trips."""

    def __init__(
        self,
        repository: TripPlanRepository | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._repository = repository or TripPlanRepository()

    def get(self, request: HttpRequest) -> HttpResponse:
        try:
            offset = max(0, int(request.GET.get("offset", 0)))
        except (ValueError, TypeError):
            offset = 0

        try:
            limit = min(50, max(1, int(request.GET.get("limit", 10))))
        except (ValueError, TypeError):
            limit = 10

        trips = self._repository.list_recent(limit=limit, offset=offset)
        total = self._repository.count_total()
        loaded_count = offset + len(trips)
        has_more = loaded_count < total

        trips_data: list[dict[str, Any]] = []
        for trip in trips:
            trips_data.append(
                {
                    "id": str(trip.id),
                    "start_input": trip.start_input,
                    "end_input": trip.end_input,
                    "total_distance_miles": str(trip.total_distance_miles),
                    "total_cost": str(trip.total_cost),
                    "dataset_version": (
                        trip.pricing_dataset.version_code
                        if trip.pricing_dataset
                        else "-"
                    ),
                    "created_at": (
                        (trip.last_requested_at or trip.created_at).strftime(
                            "%Y-%m-%d %H:%M"
                        )
                        if (trip.last_requested_at or trip.created_at)
                        else ""
                    ),
                    "detail_url": f"/trips/{trip.id}/",
                }
            )

        payload = {
            "trips": trips_data,
            "has_more": has_more,
            "next_offset": offset + len(trips),
            "loaded_count": loaded_count,
            "total": total,
        }
        return JsonResponse(payload)


class LocationsView(View):
    """Presentation view for browsing and filtering fuel station locations."""

    def get(self, request: HttpRequest) -> HttpResponse:
        q = request.GET.get("q", "").strip()
        state_filter = request.GET.get("state", "").strip().upper()

        qs = Station.objects.filter(state__in=CONTIGUOUS_48_STATES)

        if state_filter and state_filter in CONTIGUOUS_48_STATES:
            qs = qs.filter(state=state_filter)

        if q:
            qs = qs.filter(Q(city__icontains=q) | Q(state__iexact=q))

        aggregated_locations = (
            qs.values("city", "state")
            .annotate(
                station_count=Count("id"),
                min_price=Min("retail_price"),
            )
            .order_by("state", "city")
        )

        paginator = Paginator(aggregated_locations, 50)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        available_states = sorted(list(CONTIGUOUS_48_STATES))

        context = {
            "page_obj": page_obj,
            "q": q,
            "selected_state": state_filter,
            "available_states": available_states,
            "total_cities": paginator.count,
        }
        return render(request, "ui/locations.html", context)


class TripDetailView(View):
    """Presentation view for rendering an interactive map and trip breakdown."""

    def __init__(
        self,
        repository: TripPlanRepository | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._repository = repository or TripPlanRepository()

    def get(self, request: HttpRequest, trip_id: uuid.UUID) -> HttpResponse:
        trip = self._repository.get_by_id(trip_id)
        if trip is None:
            raise Http404("Trip plan does not exist.")

        route_geojson = "{}"
        if trip.route_geometry is not None:
            if hasattr(trip.route_geometry, "geojson"):
                route_geojson = str(trip.route_geometry.geojson)
            elif isinstance(trip.route_geometry, dict):
                route_geojson = json.dumps(trip.route_geometry)
            elif isinstance(trip.route_geometry, str):
                route_geojson = trip.route_geometry

        fuel_stops = list(
            trip.fuel_stops.all().select_related("station").order_by("stop_order")
        )

        stops_data: list[dict[str, Any]] = []
        for stop in fuel_stops:
            lat = float(stop.station.location.y) if stop.station.location else 0.0
            lng = float(stop.station.location.x) if stop.station.location else 0.0
            stops_data.append(
                {
                    "stop_order": stop.stop_order,
                    "station_name": stop.station.name,
                    "city": stop.station.city,
                    "state": stop.station.state,
                    "lat": lat,
                    "lng": lng,
                    "distance_from_start_miles": float(stop.distance_from_start_miles),
                    "gallons_purchased": float(stop.gallons_purchased),
                    "price_per_gallon": float(stop.price_per_gallon),
                    "cost": float(stop.cost),
                }
            )

        origin_lat = float(trip.start_point.y) if trip.start_point else 0.0
        origin_lng = float(trip.start_point.x) if trip.start_point else 0.0
        dest_lat = float(trip.end_point.y) if trip.end_point else 0.0
        dest_lng = float(trip.end_point.x) if trip.end_point else 0.0

        total_gallons_purchased = sum(
            (stop.gallons_purchased for stop in fuel_stops),
            Decimal("0.000"),
        )
        initial_fuel_gallons = getattr(trip, "initial_fuel_gallons", Decimal("50.000"))

        cache_status = request.session.pop(f"trip_cache_{trip.id}", None)
        context = {
            "trip": trip,
            "route_geojson": route_geojson,
            "fuel_stops": fuel_stops,
            "stops_json": json.dumps(stops_data),
            "origin_lat": origin_lat,
            "origin_lng": origin_lng,
            "dest_lat": dest_lat,
            "dest_lng": dest_lng,
            "total_gallons_purchased": total_gallons_purchased,
            "initial_fuel_gallons": initial_fuel_gallons,
            "cache_status": cache_status,
            "map_tile_url": getattr(settings, "MAP_TILE_URL", ""),
            "map_tile_attribution": getattr(settings, "MAP_TILE_ATTRIBUTION", ""),
            "map_tile_subdomains": getattr(settings, "MAP_TILE_SUBDOMAINS", ""),
            "map_tile_size": getattr(settings, "MAP_TILE_SIZE", 512),
            "map_tile_zoom_offset": getattr(settings, "MAP_TILE_ZOOM_OFFSET", -1),
            "map_tile_max_zoom": getattr(settings, "MAP_TILE_MAX_ZOOM", 19),
        }
        response = render(request, "ui/trip_detail.html", context)
        if cache_status:
            response["X-Cache"] = cache_status
        return response


class TripPdfView(View):
    """Generates and streams an executive PDF dispatch report for a trip."""

    def __init__(
        self,
        repository: TripPlanRepository | None = None,
        report_service: TripPdfReportService | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._repository = repository or TripPlanRepository()
        self._report_service = report_service or TripPdfReportService()

    def get(self, request: HttpRequest, trip_id: uuid.UUID) -> HttpResponse:
        trip = self._repository.get_by_id(trip_id)
        if trip is None:
            raise Http404("Trip plan does not exist.")

        pdf_bytes = self._report_service.generate_trip_pdf(trip)

        is_download = request.GET.get("download", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        disposition = "attachment" if is_download else "inline"
        filename = f"SpotterRouter-Trip-{str(trip.id)[:8]}.pdf"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        response["Content-Length"] = str(len(pdf_bytes))
        return response


class DatasetsView(View):
    """Presentation view for uploading, inspecting disk files, and managing datasets."""

    def __init__(
        self,
        service: DatasetIngestionService | None = None,
        repository: PricingDatasetRepository | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._service = service or DatasetIngestionService()
        self._repository = repository or PricingDatasetRepository()

    def get(self, request: HttpRequest) -> HttpResponse:
        disk_files = self._service.scan_dataset_directory()
        registered_datasets = list(self._repository.list_all())
        active_dataset = self._repository.get_active()
        context = {
            "disk_files": disk_files,
            "registered_datasets": registered_datasets,
            "active_dataset": active_dataset,
        }
        return render(request, "ui/datasets.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        action = request.POST.get("action", "").strip()

        if action == "upload":
            uploaded_file = request.FILES.get("dataset_file")
            if not uploaded_file or not uploaded_file.name:
                messages.error(request, "Please select a CSV file to upload.")
                return redirect("datasets")

            if not uploaded_file.name.endswith(".csv"):
                messages.error(request, "Only CSV files are supported.")
                return redirect("datasets")

            version_code = request.POST.get("version_code", "").strip() or None
            description = request.POST.get("description", "").strip()
            set_active = request.POST.get("set_active") == "on"

            try:
                dataset = self._service.ingest(
                    file_source=uploaded_file.read(),
                    filename=uploaded_file.name,
                    version_code=version_code,
                    description=description,
                    set_active=set_active,
                )
                messages.success(
                    request,
                    f"Successfully ingested dataset '{dataset.version_code}' "
                    f"({dataset.station_count} stations).",
                )
            except Exception as exc:
                messages.error(request, f"Failed to ingest dataset: {exc}")

        elif action == "ingest_disk":
            filename = request.POST.get("filename", "").strip()
            if not filename:
                messages.error(request, "Filename missing.")
                return redirect("datasets")

            target_path = self._service.get_dataset_directory() / filename
            if not target_path.exists():
                messages.error(request, f"File not found on disk: {filename}")
                return redirect("datasets")

            try:
                dataset = self._service.ingest(
                    file_source=target_path,
                    filename=filename,
                    set_active=True,
                )
                messages.success(
                    request,
                    f"Ingested and activated '{dataset.version_code}' "
                    f"({dataset.station_count} stations).",
                )
            except Exception as exc:
                messages.error(request, f"Failed to ingest disk dataset: {exc}")

        elif action == "activate":
            dataset_id = request.POST.get("dataset_id", "").strip()
            if not dataset_id:
                messages.error(request, "Dataset ID missing.")
                return redirect("datasets")

            try:
                dataset = self._service.activate_dataset(dataset_id)
                messages.success(
                    request,
                    f"Activated dataset '{dataset.version_code}' across "
                    f"{dataset.station_count} stations.",
                )
            except Exception as exc:
                messages.error(request, f"Failed to activate dataset: {exc}")

        return redirect("datasets")


class DocsView(View):
    """Presentation view for assessment documentation and VS Code explorer."""

    def __init__(
        self,
        service: DocsService | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._service = service or DocsService()

    def get(self, request: HttpRequest) -> HttpResponse:
        slug = (
            request.GET.get("doc", "").strip()
            or self._service.get_default_slug()
        )
        format_type = request.GET.get("format", "").strip()

        doc_detail = self._service.get_doc_detail(slug)
        if not doc_detail:
            default_slug = self._service.get_default_slug()
            doc_detail = self._service.get_doc_detail(default_slug)
            if not doc_detail:
                raise Http404(f"Documentation not found for slug: {slug}")

        # Support fast client-side async switching with JSON payload
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        if format_type == "json" or is_ajax:
            return JsonResponse(
                {
                    "slug": doc_detail.metadata.slug,
                    "title": doc_detail.metadata.title,
                    "category_id": doc_detail.metadata.category_id,
                    "category_title": doc_detail.metadata.category_title,
                    "filename": doc_detail.metadata.filename,
                    "summary": doc_detail.metadata.summary,
                    "reading_time_minutes": (
                        doc_detail.metadata.reading_time_minutes
                    ),
                    "html_content": doc_detail.html_content,
                    "table_of_contents": [
                        {
                            "level": t.level,
                            "title": t.title,
                            "slug": t.slug,
                        }
                        for t in doc_detail.table_of_contents
                    ],
                    "previous_doc": (
                        {
                            "slug": doc_detail.previous_doc.slug,
                            "title": doc_detail.previous_doc.title,
                        }
                        if doc_detail.previous_doc
                        else None
                    ),
                    "next_doc": (
                        {
                            "slug": doc_detail.next_doc.slug,
                            "title": doc_detail.next_doc.title,
                        }
                        if doc_detail.next_doc
                        else None
                    ),
                }
            )

        categories = self._service.get_categories()
        context = {
            "categories": categories,
            "active_doc": doc_detail,
            "active_slug": doc_detail.metadata.slug,
            "active_category_id": doc_detail.metadata.category_id,
        }
        return render(request, "ui/docs.html", context)

