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
    assert "SPEEDWAY #100" in response.context["stops_json"]

    content = response.content.decode()
    assert "Chicago, IL" in content
    assert "Dallas, TX" in content
    assert "Total Estimated Fuel Cost" in content
    assert "AI Route Rationale" in content
    assert 'id="map"' in content
    assert "SPEEDWAY #100" in content


def test_trip_detail_view_not_found(client: Client, db: None) -> None:
    import uuid

    url = reverse("trip-detail", kwargs={"trip_id": uuid.uuid4()})
    response = client.get(url)

    assert response.status_code == 404
