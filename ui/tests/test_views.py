import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import LineString, Point
from django.test import Client
from django.urls import reverse

from core.exceptions import GeocodingUnresolvedError
from stations.models import Station
from trips.models import FuelStop, TripPlan


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def sample_trip_plan(db: None) -> TripPlan:
    station = Station.objects.create(
        opis_id="UI_TEST_01",
        name="SPEEDWAY #100",
        city="Lafayette",
        state="IN",
        retail_price=Decimal("3.129"),
        location=Point(-86.87, 40.41, srid=4326),
    )
    plan = TripPlan.objects.create(
        start_input="Chicago, IL",
        end_input="Dallas, TX",
        start_point=Point(-87.6298, 41.8781, srid=4326),
        end_point=Point(-96.7970, 32.7767, srid=4326),
        route_geometry=LineString(
            [(-87.6298, 41.8781), (-96.7970, 32.7767)],
            srid=4326,
        ),
        total_distance_miles=Decimal("967.30"),
        total_gallons=Decimal("96.730"),
        total_cost=Decimal("302.66"),
        cache_key="ui_test_cache_key",
        ai_explanation="Test AI explanation rationale.",
    )
    FuelStop.objects.create(
        trip_plan=plan,
        station=station,
        stop_order=1,
        distance_from_start_miles=Decimal("415.00"),
        gallons_purchased=Decimal("41.500"),
        price_per_gallon=Decimal("3.129"),
        cost=Decimal("129.85"),
    )
    return plan


def test_home_view_get(client: Client, sample_trip_plan: TripPlan) -> None:
    url = reverse("home")
    response = client.get(url)

    assert response.status_code == 200
    assert "recent_trips" in response.context
    assert "presets" in response.context
    assert len(response.context["recent_trips"]) >= 1
    assert "Chicago, IL" in response.content.decode()
    assert "Dallas, TX" in response.content.decode()
    assert "Chicago, IL to Dallas, TX" in response.content.decode()


def test_home_view_post_valid(client: Client, sample_trip_plan: TripPlan) -> None:
    url = reverse("home")
    with patch(
        "trips.services.TripPlanningService.plan_trip",
        return_value=sample_trip_plan,
    ) as mock_plan:
        response = client.post(
            url,
            {"start": "Chicago, IL", "end": "Dallas, TX"},
        )

    assert response.status_code == 302
    expected_url = reverse(
        "trip-detail",
        kwargs={"trip_id": sample_trip_plan.id},
    )
    assert response["Location"] == expected_url
    mock_plan.assert_called_once_with(
        start_input="Chicago, IL",
        end_input="Dallas, TX",
    )


def test_home_view_post_empty_inputs(client: Client, db: None) -> None:
    url = reverse("home")
    response = client.post(url, {"start": "", "end": ""})

    assert response.status_code == 400
    assert "error" in response.context
    content = response.content.decode()
    assert "Both start and destination locations are required" in content


def test_home_view_post_domain_error(client: Client, db: None) -> None:
    url = reverse("home")
    with patch(
        "trips.services.TripPlanningService.plan_trip",
        side_effect=GeocodingUnresolvedError("Unable to resolve location: Atlantis"),
    ):
        response = client.post(
            url,
            {"start": "Chicago, IL", "end": "Atlantis"},
        )

    assert response.status_code == 400
    assert "error" in response.context
    assert "Unable to resolve location: Atlantis" in response.content.decode()


def test_trip_detail_view_get_success(
    client: Client, sample_trip_plan: TripPlan
) -> None:
    url = reverse("trip-detail", kwargs={"trip_id": sample_trip_plan.id})
    response = client.get(url)

    assert response.status_code == 200
    assert "trip" in response.context
    assert "route_geojson" in response.context
    assert "fuel_stops" in response.context
    assert "stops_json" in response.context
    assert "total_gallons_purchased" in response.context
    assert "initial_fuel_gallons" in response.context
    assert "SPEEDWAY #100" in response.context["stops_json"]

    content = response.content.decode()
    assert "Chicago, IL" in content
    assert "Dallas, TX" in content
    assert "Total Refuel Cost" in content
    assert "Fuel Purchased En Route" in content
    assert "Analysis" in content
    assert "DeepSeek" not in content
    assert '<th style="width: 70px;">Stop</th>' in content
    assert '<th style="width: 70px;">Stop #</th>' not in content
    assert 'id="map"' in content
    assert "SPEEDWAY #100" in content


def test_trip_detail_view_not_found(client: Client, db: None) -> None:
    import uuid

    url = reverse("trip-detail", kwargs={"trip_id": uuid.uuid4()})
    response = client.get(url)

    assert response.status_code == 404


def test_base_navigation_and_branding(
    client: Client, sample_trip_plan: TripPlan
) -> None:
    url = reverse("home")
    response = client.get(url)

    content = response.content.decode()
    assert "SpotterRouter" in content
    assert "spotterrouter.mahboob.engineer" in content
    assert ">Plan Trip<" not in content
    assert ">REST API<" not in content
    assert ">Health<" not in content
    assert "Locations" in content
    assert reverse("locations") in content


def test_home_view_prefills_from_get_params(client: Client, db: None) -> None:
    url = reverse("home")
    response = client.get(url, {"start": "Austin, TX", "end": "Houston, TX"})

    assert response.status_code == 200
    assert response.context["start"] == "Austin, TX"
    assert response.context["end"] == "Houston, TX"
    content = response.content.decode()
    assert 'value="Austin, TX"' in content
    assert 'value="Houston, TX"' in content


def test_home_view_pagination_limit_10(client: Client, db: None) -> None:
    for i in range(15):
        TripPlan.objects.create(
            start_input=f"City{i}, IL",
            end_input="Dallas, TX",
            start_point=Point(-87.6, 41.8, srid=4326),
            end_point=Point(-96.8, 32.7, srid=4326),
            route_geometry=LineString([(-87.6, 41.8), (-96.8, 32.7)], srid=4326),
            total_distance_miles=Decimal("500.00"),
            total_gallons=Decimal("50.000"),
            total_cost=Decimal("150.00"),
            cache_key=f"pagination_test_key_{i}",
        )

    url = reverse("home")
    response = client.get(url)

    assert response.status_code == 200
    assert len(response.context["recent_trips"]) == 10
    assert response.context["has_more"] is True
    assert response.context["total_trips"] == 15
    assert "Load More Trips" in response.content.decode()


def test_recent_trips_api_view(client: Client, db: None) -> None:
    for i in range(15):
        TripPlan.objects.create(
            start_input=f"City{i}, IL",
            end_input="Dallas, TX",
            start_point=Point(-87.6, 41.8, srid=4326),
            end_point=Point(-96.8, 32.7, srid=4326),
            route_geometry=LineString([(-87.6, 41.8), (-96.8, 32.7)], srid=4326),
            total_distance_miles=Decimal("500.00"),
            total_gallons=Decimal("50.000"),
            total_cost=Decimal("150.00"),
            cache_key=f"api_test_key_{i}",
        )

    url = reverse("recent-trips")
    response = client.get(url, {"offset": 10, "limit": 10})

    assert response.status_code == 200
    data = response.json()
    assert len(data["trips"]) == 5
    assert data["has_more"] is False
    assert data["loaded_count"] == 15
    assert data["total"] == 15


def test_locations_view_renders_successfully(client: Client, db: None) -> None:
    Station.objects.create(
        opis_id="LOC_TEST_01",
        name="LOVES TRAVEL STOP #1",
        city="Indianapolis",
        state="IN",
        retail_price=Decimal("3.199"),
        location=Point(-86.15, 39.76, srid=4326),
    )
    url = reverse("locations")
    response = client.get(url)

    assert response.status_code == 200
    assert "page_obj" in response.context
    assert response.context["total_cities"] >= 1
    content = response.content.decode()
    assert "Indianapolis" in content
    assert "IN" in content
    assert "Locations Directory" in content
    assert "Copy" in content
    assert "Set as Origin" in content
    assert "Set as Destination" in content


def test_locations_view_filter_and_search(client: Client, db: None) -> None:
    Station.objects.create(
        opis_id="LOC_TEST_02",
        name="PILOT #2",
        city="Columbus",
        state="OH",
        retail_price=Decimal("3.249"),
        location=Point(-82.99, 39.96, srid=4326),
    )
    Station.objects.create(
        opis_id="LOC_TEST_03",
        name="FLYING J #3",
        city="Dallas",
        state="TX",
        retail_price=Decimal("2.999"),
        location=Point(-96.79, 32.77, srid=4326),
    )

    url = reverse("locations")

    # Search by city
    resp_search = client.get(url, {"q": "Columbus"})
    assert resp_search.status_code == 200
    content_search = resp_search.content.decode()
    assert "Columbus, OH" in content_search
    assert "Dallas, TX" not in content_search

    # Filter by state
    resp_state = client.get(url, {"state": "TX"})
    assert resp_state.status_code == 200
    content_state = resp_state.content.decode()
    assert "Dallas, TX" in content_state
    assert "Columbus, OH" not in content_state


def test_dark_mode_toggle_present_after_locations(client: Client, db: None) -> None:
    url = reverse("home")
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()

    # Verify theme toggle button exists with "Dark" text (no emojis, no "Night Mode")
    assert 'id="theme-toggle"' in content
    assert 'id="theme-text">Dark<' in content
    assert "Night Mode" not in content
    assert "🌙" not in content
    assert "☀️" not in content

    # Verify navigation order: Locations -> Add Dataset -> theme toggle
    loc_pos = content.find(reverse("locations"))
    ds_pos = content.find(reverse("datasets"))
    toggle_pos = content.find('id="theme-toggle"')
    assert loc_pos != -1
    assert ds_pos != -1
    assert toggle_pos != -1
    assert loc_pos < ds_pos < toggle_pos


def test_base_contains_fouc_prevention_script(client: Client, db: None) -> None:
    url = reverse("home")
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()

    assert "spotterrouter_theme" in content
    assert "document.documentElement.setAttribute('data-theme', theme);" in content


def test_hero_ambient_and_grid_markup(client: Client, db: None) -> None:
    url = reverse("home")
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()

    assert "hero-container" in content
    assert "hero-ambient-layer" in content
    assert "hero-grid-overlay" in content
    assert "Contiguous US Fleet Route Engine" in content
    assert "Quick Benchmark Presets" in content
    assert "shiftAmbientHues" in content


def test_datasets_view_get_renders_successfully(client: Client, db: None) -> None:
    from stations.models import PricingDataset

    PricingDataset.objects.create(
        version_code="TEST-UI-DS-1",
        filename="test_ds.csv",
        file_hash="hash_ui_ds_1",
        station_count=100,
        is_active=True,
    )

    url = reverse("datasets")
    response = client.get(url)

    assert response.status_code == 200
    assert "disk_files" in response.context
    assert "registered_datasets" in response.context
    assert "active_dataset" in response.context
    content = response.content.decode()
    assert "Fuel Pricing Datasets &amp; Ingestion" in content
    assert "Upload New CSV Dataset" in content
    assert "TEST-UI-DS-1" in content


def test_datasets_view_post_upload_valid_csv(client: Client, db: None) -> None:
    from pathlib import Path

    from django.core.files.uploadedfile import SimpleUploadedFile

    from stations.models import PricingDataset
    from stations.tests.test_dataset_service import SAMPLE_CSV

    uploaded_filename = "test_uploaded_temp.csv"
    created_path = Path("dataset") / uploaded_filename
    try:
        uploaded = SimpleUploadedFile(
            uploaded_filename,
            SAMPLE_CSV.encode("utf-8"),
            content_type="text/csv",
        )
        url = reverse("datasets")
        response = client.post(
            url,
            {
                "action": "upload",
                "dataset_file": uploaded,
                "version_code": "UPLOAD-V1",
                "description": "Test upload",
                "set_active": "on",
            },
        )

        assert response.status_code == 302
        assert response["Location"] == reverse("datasets")

        ds = PricingDataset.objects.filter(version_code="UPLOAD-V1").first()
        assert ds is not None
        assert ds.is_active is True
        assert ds.station_count == 3
    finally:
        created_path.unlink(missing_ok=True)


def test_datasets_view_post_upload_invalid_file(client: Client, db: None) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    uploaded = SimpleUploadedFile(
        "invalid_file.txt",
        b"Not a CSV",
        content_type="text/plain",
    )
    url = reverse("datasets")
    response = client.post(
        url,
        {
            "action": "upload",
            "dataset_file": uploaded,
        },
    )
    assert response.status_code == 302


def test_datasets_view_post_activate(client: Client, db: None) -> None:
    from stations.models import PricingDataset

    d1 = PricingDataset.objects.create(
        version_code="OLD-DS",
        filename="old.csv",
        file_hash="hash_old",
        station_count=10,
        is_active=True,
    )
    d2 = PricingDataset.objects.create(
        version_code="NEW-DS",
        filename="new.csv",
        file_hash="hash_new",
        station_count=20,
        is_active=False,
    )

    url = reverse("datasets")
    response = client.post(
        url,
        {
            "action": "activate",
            "dataset_id": str(d2.id),
        },
    )
    assert response.status_code == 302
    d1.refresh_from_db()
    d2.refresh_from_db()
    assert d2.is_active is True
    assert d1.is_active is False


def test_recent_trips_api_view_includes_dataset_version(
    client: Client, db: None
) -> None:
    from stations.models import PricingDataset

    ds = PricingDataset.objects.create(
        version_code="OPIS-2026-TESTVER",
        filename="test.csv",
        file_hash="hash_testver",
        station_count=50,
        is_active=True,
    )
    TripPlan.objects.create(
        start_input="Chicago, IL",
        end_input="Dallas, TX",
        start_point=Point(-87.6, 41.8, srid=4326),
        end_point=Point(-96.8, 32.7, srid=4326),
        route_geometry=LineString([(-87.6, 41.8), (-96.8, 32.7)], srid=4326),
        total_distance_miles=Decimal("500.00"),
        total_gallons=Decimal("50.000"),
        total_cost=Decimal("150.00"),
        cache_key="api_version_test_key",
        pricing_dataset=ds,
    )

    url = reverse("recent-trips")
    response = client.get(url, {"offset": 0, "limit": 5})

    assert response.status_code == 200
    data = response.json()
    assert len(data["trips"]) >= 1
    assert data["trips"][0]["dataset_version"] == "OPIS-2026-TESTVER"


def test_trip_detail_view_shows_dataset_version_badge(
    client: Client, sample_trip_plan: TripPlan
) -> None:
    from stations.models import PricingDataset

    ds = PricingDataset.objects.create(
        version_code="OPIS-DETAIL-V1",
        filename="detail.csv",
        file_hash="hash_detail_1",
        station_count=100,
        is_active=True,
    )
    sample_trip_plan.pricing_dataset = ds
    sample_trip_plan.save(update_fields=["pricing_dataset"])

    url = reverse("trip-detail", kwargs={"trip_id": sample_trip_plan.id})
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Pricing Dataset:" in content
    assert "OPIS-DETAIL-V1" in content


def test_trip_detail_view_has_export_pdf_button(
    client: Client, sample_trip_plan: TripPlan
) -> None:
    url = reverse("trip-detail", kwargs={"trip_id": sample_trip_plan.id})
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    pdf_url = reverse("trip-pdf", kwargs={"trip_id": sample_trip_plan.id})
    assert "Export to PDF" in content
    assert pdf_url in content



def test_trip_pdf_view_inline(
    client: Client, sample_trip_plan: TripPlan
) -> None:
    url = reverse("trip-pdf", kwargs={"trip_id": sample_trip_plan.id})
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert "inline" in response["Content-Disposition"]
    assert f"SpotterRouter-Trip-{str(sample_trip_plan.id)[:8]}.pdf" in response[
        "Content-Disposition"
    ]
    assert response.content.startswith(b"%PDF-1.")


def test_trip_pdf_view_download_attachment(
    client: Client, sample_trip_plan: TripPlan
) -> None:
    url = reverse("trip-pdf", kwargs={"trip_id": sample_trip_plan.id})
    response = client.get(url, {"download": "1"})

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert "attachment" in response["Content-Disposition"]
    assert f"SpotterRouter-Trip-{str(sample_trip_plan.id)[:8]}.pdf" in response[
        "Content-Disposition"
    ]
    assert response.content.startswith(b"%PDF-1.")


def test_trip_pdf_view_not_found(client: Client, db: None) -> None:
    missing_id = uuid.uuid4()
    url = reverse("trip-pdf", kwargs={"trip_id": missing_id})
    response = client.get(url)

    assert response.status_code == 404

