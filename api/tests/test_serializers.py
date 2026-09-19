from decimal import Decimal

import pytest
from django.contrib.gis.geos import LineString, Point

from api.serializers import (
    FuelStopResponseSerializer,
    TripPlanListSerializer,
    TripPlanRequestSerializer,
    TripPlanResponseSerializer,
)
from stations.models import Station
from trips.models import FuelStop, TripPlan


def test_trip_plan_request_serializer_valid() -> None:
    data = {"start": "Chicago, IL", "end": "Dallas, TX"}
    serializer = TripPlanRequestSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data == {
        "start": "Chicago, IL",
        "end": "Dallas, TX",
    }


def test_trip_plan_request_serializer_trims_whitespace() -> None:
    data = {"start": "  Chicago, IL  ", "end": "  Dallas, TX  "}
    serializer = TripPlanRequestSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data == {
        "start": "Chicago, IL",
        "end": "Dallas, TX",
    }


@pytest.mark.parametrize(
    "invalid_payload,expected_error_field",
    [
        ({"end": "Dallas, TX"}, "start"),
        ({"start": "Chicago, IL"}, "end"),
        ({"start": "", "end": "Dallas, TX"}, "start"),
        ({"start": "   ", "end": "Dallas, TX"}, "start"),
        ({"start": "Chicago, IL", "end": ""}, "end"),
        ({"start": "Chicago, IL", "end": "   "}, "end"),
    ],
)
def test_trip_plan_request_serializer_invalid_inputs(
    invalid_payload: dict[str, str],
    expected_error_field: str,
) -> None:
    serializer = TripPlanRequestSerializer(data=invalid_payload)
    assert not serializer.is_valid()
    assert expected_error_field in serializer.errors


@pytest.mark.django_db
def test_fuel_stop_response_serializer() -> None:
    station = Station.objects.create(
        opis_id="TEST_001",
        name="TA TEST STATION",
        city="Bridgeport",
        state="MI",
        retail_price=Decimal("3.269"),
        location=Point(-83.88, 43.35, srid=4326),
    )
    trip_plan = TripPlan.objects.create(
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
        total_cost=Decimal("341.52"),
        cache_key="test_cache_key",
    )
    stop = FuelStop.objects.create(
        trip_plan=trip_plan,
        station=station,
        stop_order=1,
        distance_from_start_miles=Decimal("410.00"),
        gallons_purchased=Decimal("41.000"),
        price_per_gallon=Decimal("3.269"),
        cost=Decimal("134.03"),
    )

    serializer = FuelStopResponseSerializer(stop)
    data = serializer.data

    assert data["stop_order"] == 1
    assert data["station_name"] == "TA TEST STATION"
    assert data["city"] == "Bridgeport"
    assert data["state"] == "MI"
    assert data["distance_from_start_miles"] == Decimal("410.00")
    assert data["gallons_purchased"] == Decimal("41.000")
    assert data["price_per_gallon"] == Decimal("3.269")
    assert data["cost"] == Decimal("134.03")


@pytest.mark.django_db
def test_trip_plan_response_serializer() -> None:
    station = Station.objects.create(
        opis_id="TEST_002",
        name="PETRO DALLAS",
        city="Dallas",
        state="TX",
        retail_price=Decimal("3.150"),
        location=Point(-96.79, 32.77, srid=4326),
    )
    trip_plan = TripPlan.objects.create(
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
        total_cost=Decimal("341.52"),
        cache_key="test_response_key",
        ai_explanation=None,
    )
    FuelStop.objects.create(
        trip_plan=trip_plan,
        station=station,
        stop_order=1,
        distance_from_start_miles=Decimal("410.00"),
        gallons_purchased=Decimal("41.000"),
        price_per_gallon=Decimal("3.150"),
        cost=Decimal("129.15"),
    )

    serializer = TripPlanResponseSerializer(trip_plan)
    data = serializer.data

    assert str(data["id"]) == str(trip_plan.id)
    assert data["start_input"] == "Chicago, IL"
    assert data["end_input"] == "Dallas, TX"
    assert data["total_distance_miles"] == Decimal("967.30")
    assert data["total_gallons"] == Decimal("96.730")
    assert data["total_cost"] == Decimal("341.52")
    assert data["ai_explanation"] is None
    assert "created_at" in data

    # Route geometry should be a GeoJSON LineString dictionary
    assert isinstance(data["route_geometry"], dict)
    assert data["route_geometry"]["type"] == "LineString"
    assert len(data["route_geometry"]["coordinates"]) == 2
    assert data["route_geometry"]["coordinates"][0] == [-87.6298, 41.8781]

    # Nested fuel stops
    assert len(data["fuel_stops"]) == 1
    assert data["fuel_stops"][0]["station_name"] == "PETRO DALLAS"


@pytest.mark.django_db
def test_trip_plan_list_serializer() -> None:
    trip_plan = TripPlan.objects.create(
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
        total_cost=Decimal("341.52"),
        cache_key="test_list_key",
    )

    serializer = TripPlanListSerializer(trip_plan)
    data = serializer.data

    assert str(data["id"]) == str(trip_plan.id)
    assert data["start_input"] == "Chicago, IL"
    assert data["end_input"] == "Dallas, TX"
    assert data["total_distance_miles"] == Decimal("967.30")
    assert data["total_cost"] == Decimal("341.52")
    assert "created_at" in data
    assert "route_geometry" not in data
    assert "fuel_stops" not in data
