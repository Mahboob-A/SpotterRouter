import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import LineString, Point
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.exceptions import (
    GeocodingUnresolvedError,
    InsufficientStationCoverageError,
    RoutingUnavailableError,
)
from stations.models import Station
from trips.models import FuelStop, TripPlan


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def sample_trip_plan(db: None) -> TripPlan:
    station = Station.objects.create(
        opis_id="TEST_STOP_01",
        name="PILOT TRAVEL CENTER",
        city="Gary",
        state="IN",
        retail_price=Decimal("3.199"),
        location=Point(-87.34, 41.59, srid=4326),
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
        total_cost=Decimal("309.44"),
        cache_key="test_sample_trip_key",
        ai_explanation=None,
    )
    FuelStop.objects.create(
        trip_plan=plan,
        station=station,
        stop_order=1,
        distance_from_start_miles=Decimal("420.00"),
        gallons_purchased=Decimal("42.000"),
        price_per_gallon=Decimal("3.199"),
        cost=Decimal("134.36"),
    )
    return plan


def test_post_trips_success(api_client: APIClient, sample_trip_plan: TripPlan) -> None:
    url = reverse("trip-plan-list-create")
    with patch(
        "trips.services.TripPlanningService.plan_trip",
        return_value=sample_trip_plan,
    ) as mock_plan:
        response = api_client.post(
            url,
            {"start": "Chicago, IL", "end": "Dallas, TX"},
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert str(data["id"]) == str(sample_trip_plan.id)
    assert data["start_input"] == "Chicago, IL"
    assert data["end_input"] == "Dallas, TX"
    assert data["total_distance_miles"] == 967.3
    assert data["total_cost"] == 309.44
    assert data["route_geometry"]["type"] == "LineString"
    assert len(data["fuel_stops"]) == 1
    assert data["fuel_stops"][0]["station_name"] == "PILOT TRAVEL CENTER"
    assert response.headers["X-Cache"] == "MISS"
    mock_plan.assert_called_once_with(
        start_input="Chicago, IL",
        end_input="Dallas, TX",
        force_refresh=False,
    )


def test_post_trips_xcache_header_hit_and_force_refresh(
    api_client: APIClient, sample_trip_plan: TripPlan
) -> None:
    url = reverse("trip-plan-list-create")

    sample_trip_plan.is_cache_hit = True
    with patch(
        "trips.services.TripPlanningService.plan_trip",
        return_value=sample_trip_plan,
    ) as mock_plan:
        response = api_client.post(
            url,
            {"start": "Chicago, IL", "end": "Dallas, TX"},
            format="json",
        )
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["X-Cache"] == "HIT"
    mock_plan.assert_called_once_with(
        start_input="Chicago, IL",
        end_input="Dallas, TX",
        force_refresh=False,
    )

    sample_trip_plan.is_cache_hit = False
    with patch(
        "trips.services.TripPlanningService.plan_trip",
        return_value=sample_trip_plan,
    ) as mock_plan_refresh:
        response_refresh = api_client.post(
            url,
            {"start": "Chicago, IL", "end": "Dallas, TX", "force_refresh": True},
            format="json",
        )
    assert response_refresh.status_code == status.HTTP_200_OK
    assert response_refresh.headers["X-Cache"] == "MISS"
    mock_plan_refresh.assert_called_once_with(
        start_input="Chicago, IL",
        end_input="Dallas, TX",
        force_refresh=True,
    )


def test_post_trips_invalid_payload(api_client: APIClient) -> None:
    url = reverse("trip-plan-list-create")
    response = api_client.post(url, {"start": ""}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"] == "invalid_request"
    assert "start" in data["detail"]


def test_post_trips_geocoding_unresolved(api_client: APIClient) -> None:
    url = reverse("trip-plan-list-create")
    with patch(
        "trips.services.TripPlanningService.plan_trip",
        side_effect=GeocodingUnresolvedError("Could not resolve 'Atlantis'"),
    ):
        response = api_client.post(
            url,
            {"start": "Chicago, IL", "end": "Atlantis"},
            format="json",
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["error"] == "unresolvable_location"
    assert "Atlantis" in data["detail"]


def test_post_trips_routing_unavailable(api_client: APIClient) -> None:
    url = reverse("trip-plan-list-create")
    with patch(
        "trips.services.TripPlanningService.plan_trip",
        side_effect=RoutingUnavailableError("OSRM connection timed out"),
    ):
        response = api_client.post(
            url,
            {"start": "Chicago, IL", "end": "Dallas, TX"},
            format="json",
        )

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    data = response.json()
    assert data["error"] == "routing_unavailable"
    assert "OSRM connection timed out" in data["detail"]


def test_post_trips_insufficient_coverage(api_client: APIClient) -> None:
    url = reverse("trip-plan-list-create")
    with patch(
        "trips.services.TripPlanningService.plan_trip",
        side_effect=InsufficientStationCoverageError("No station within vehicle range"),
    ):
        response = api_client.post(
            url,
            {"start": "Chicago, IL", "end": "Dallas, TX"},
            format="json",
        )

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    data = response.json()
    assert data["error"] == "insufficient_station_coverage"
    assert "No station within vehicle range" in data["detail"]


def test_get_trips_list_success(
    api_client: APIClient, sample_trip_plan: TripPlan
) -> None:
    url = reverse("trip-plan-list-create")
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) >= 1
    item = data["results"][0]
    assert str(item["id"]) == str(sample_trip_plan.id)
    assert item["start_input"] == "Chicago, IL"
    assert item["end_input"] == "Dallas, TX"
    assert item["total_distance_miles"] == 967.3
    assert item["total_cost"] == 309.44
    assert "created_at" in item
    assert "route_geometry" not in item
    assert "fuel_stops" not in item


def test_get_trip_detail_success(
    api_client: APIClient, sample_trip_plan: TripPlan
) -> None:
    url = reverse("trip-plan-detail", kwargs={"trip_id": sample_trip_plan.id})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert str(data["id"]) == str(sample_trip_plan.id)
    assert data["start_input"] == "Chicago, IL"
    assert data["end_input"] == "Dallas, TX"
    assert data["total_distance_miles"] == 967.3
    assert data["total_cost"] == 309.44
    assert data["route_geometry"]["type"] == "LineString"
    assert len(data["fuel_stops"]) == 1
    assert data["fuel_stops"][0]["station_name"] == "PILOT TRAVEL CENTER"


def test_get_trip_detail_not_found(api_client: APIClient, db: None) -> None:
    random_uuid = uuid.uuid4()
    url = reverse("trip-plan-detail", kwargs={"trip_id": random_uuid})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["error"] == "not_found"
    assert "detail" in data


def test_unsupported_method_trips(api_client: APIClient) -> None:
    url = reverse("trip-plan-list-create")
    response = api_client.put(url, {}, format="json")

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    data = response.json()
    assert data["error"] == "method_not_allowed"
    assert "detail" in data
