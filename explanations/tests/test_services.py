from decimal import Decimal
from unittest.mock import MagicMock

from django.contrib.gis.geos import LineString, Point

from explanations.adapters import LLMClient
from explanations.services import ExplanationService
from stations.models import Station
from trips.models import FuelStop, TripPlan


def _create_trip_plan(
    distance_miles: str = "400.00",
    total_gallons: str = "40.000",
    total_cost: str = "0.00",
) -> TripPlan:
    return TripPlan(
        start_input="Chicago, IL",
        end_input="Indianapolis, IN",
        start_point=Point(-87.6298, 41.8781, srid=4326),
        end_point=Point(-86.1581, 39.7684, srid=4326),
        route_geometry=LineString(
            [(-87.6298, 41.8781), (-86.1581, 39.7684)],
            srid=4326,
        ),
        total_distance_miles=Decimal(distance_miles),
        total_gallons=Decimal(total_gallons),
        total_cost=Decimal(total_cost),
        cache_key="test-key-12345",
    )


def test_build_prompt_zero_stops() -> None:
    plan = _create_trip_plan(
        distance_miles="350.00", total_gallons="35.000", total_cost="0.00"
    )
    plan._prefetched_objects_cache = {  # type: ignore[attr-defined]
        "fuel_stops": [],
    }

    service = ExplanationService(llm_client=MagicMock(spec=LLMClient))
    prompt = service.build_prompt(plan)

    assert "Chicago, IL" in prompt
    assert "Indianapolis, IN" in prompt
    assert "350.00 miles" in prompt
    assert "no fuel stops" in prompt.lower() or "without refueling" in prompt.lower()


def test_build_prompt_with_fuel_stops() -> None:
    plan = _create_trip_plan(
        distance_miles="950.00", total_gallons="95.000", total_cost="275.50"
    )
    station1 = Station(
        id=1,
        opis_id="1001",
        name="Pilot Travel Center",
        city="Effingham",
        state="IL",
        retail_price=Decimal("2.850"),
    )
    stop1 = FuelStop(
        trip_plan=plan,
        station=station1,
        stop_order=1,
        distance_from_start_miles=Decimal("210.50"),
        gallons_purchased=Decimal("50.000"),
        price_per_gallon=Decimal("2.850"),
        cost=Decimal("142.50"),
    )
    station2 = Station(
        id=2,
        opis_id="1002",
        name="Love's Travel Stop",
        city="Mount Vernon",
        state="IL",
        retail_price=Decimal("2.660"),
    )
    stop2 = FuelStop(
        trip_plan=plan,
        station=station2,
        stop_order=2,
        distance_from_start_miles=Decimal("450.00"),
        gallons_purchased=Decimal("50.000"),
        price_per_gallon=Decimal("2.660"),
        cost=Decimal("133.00"),
    )
    plan._prefetched_objects_cache = {  # type: ignore[attr-defined]
        "fuel_stops": [stop1, stop2],
    }

    service = ExplanationService(llm_client=MagicMock(spec=LLMClient))
    prompt = service.build_prompt(plan)

    assert "Pilot Travel Center" in prompt
    assert "Effingham, IL" in prompt
    assert "$2.85" in prompt
    assert "Love's Travel Stop" in prompt
    assert "Mount Vernon, IL" in prompt
    assert "$2.66" in prompt
    assert "2-4 sentences" in prompt


def test_explain_invokes_llm_client() -> None:
    plan = _create_trip_plan(distance_miles="350.00")
    plan._prefetched_objects_cache = {  # type: ignore[attr-defined]
        "fuel_stops": [],
    }

    mock_client = MagicMock(spec=LLMClient)
    mock_client.generate_explanation.return_value = (
        "The trip is 350 miles, which is within the 500-mile initial range."
    )

    service = ExplanationService(llm_client=mock_client)
    explanation = service.explain(plan)

    assert explanation == (
        "The trip is 350 miles, which is within the 500-mile initial range."
    )
    mock_client.generate_explanation.assert_called_once()
    call_args = mock_client.generate_explanation.call_args
    assert "Chicago, IL" in call_args.args[0]
    assert call_args.kwargs["system_prompt"] is not None


def test_build_fallback_explanation_zero_stops() -> None:
    plan = _create_trip_plan(distance_miles="320.00")
    plan._prefetched_objects_cache = {  # type: ignore[attr-defined]
        "fuel_stops": [],
    }
    service = ExplanationService()
    fallback = service.build_fallback_explanation(plan)

    assert "320.00 miles" in fallback
    assert "within the commercial vehicle's 500-mile operating range" in fallback
    assert "No en-route refueling stops are required" in fallback


def test_build_fallback_explanation_with_stops() -> None:
    plan = _create_trip_plan(
        distance_miles="900.00", total_gallons="90.000", total_cost="260.00"
    )
    station = Station(
        id=1,
        opis_id="ST-101",
        name="Speedway #400",
        city="Indianapolis",
        state="IN",
        retail_price=Decimal("2.890"),
    )
    stop = FuelStop(
        trip_plan=plan,
        station=station,
        stop_order=1,
        distance_from_start_miles=Decimal("400.00"),
        gallons_purchased=Decimal("40.000"),
        price_per_gallon=Decimal("2.890"),
        cost=Decimal("115.60"),
    )
    plan._prefetched_objects_cache = {  # type: ignore[attr-defined]
        "fuel_stops": [stop],
    }
    service = ExplanationService()
    fallback = service.build_fallback_explanation(plan)

    assert "1 fuel stop(s) over 900.00 miles" in fallback
    assert "Speedway #400 in Indianapolis, IN" in fallback
    assert "$2.890/gal" in fallback
    assert "$260.00" in fallback

