import uuid
from decimal import Decimal
from unittest.mock import MagicMock

from django.contrib.gis.geos import LineString, Point

from explanations.exceptions import LLMServiceError
from explanations.services import ExplanationService
from explanations.tasks import generate_trip_explanation
from trips.caching import TripCacheManager
from trips.models import TripPlan
from trips.repositories import TripPlanRepository


def _make_sample_trip(has_explanation: bool = False) -> TripPlan:
    return TripPlan(
        id=uuid.uuid4(),
        start_input="Chicago, IL",
        end_input="Dallas, TX",
        start_point=Point(-87.6298, 41.8781, srid=4326),
        end_point=Point(-96.7970, 32.7767, srid=4326),
        route_geometry=LineString(
            [(-87.6298, 41.8781), (-96.7970, 32.7767)],
            srid=4326,
        ),
        total_distance_miles=Decimal("950.00"),
        total_gallons=Decimal("95.000"),
        total_cost=Decimal("250.00"),
        cache_key="sample-trip-key",
        ai_explanation="Existing rationale" if has_explanation else None,
    )


def test_generate_trip_explanation_success() -> None:
    trip = _make_sample_trip(has_explanation=False)
    mock_repo = MagicMock(spec=TripPlanRepository)
    mock_repo.get_by_id.return_value = trip

    mock_service = MagicMock(spec=ExplanationService)
    mock_service.explain.return_value = "Optimal stops selected along I-55."

    mock_cache = MagicMock(spec=TripCacheManager)

    generate_trip_explanation(
        trip_id=str(trip.id),
        trip_repository=mock_repo,
        explanation_service=mock_service,
        cache_manager=mock_cache,
    )

    mock_repo.get_by_id.assert_called_once_with(trip.id)
    mock_service.explain.assert_called_once_with(trip)
    mock_repo.update_explanation.assert_called_once_with(
        trip.id, "Optimal stops selected along I-55."
    )
    mock_cache.set.assert_called_once_with(trip)
    assert trip.ai_explanation == "Optimal stops selected along I-55."


def test_generate_trip_explanation_invalid_uuid() -> None:
    mock_repo = MagicMock(spec=TripPlanRepository)
    mock_service = MagicMock(spec=ExplanationService)
    mock_cache = MagicMock(spec=TripCacheManager)

    generate_trip_explanation(
        trip_id="not-a-valid-uuid",
        trip_repository=mock_repo,
        explanation_service=mock_service,
        cache_manager=mock_cache,
    )

    mock_repo.get_by_id.assert_not_called()
    mock_service.explain.assert_not_called()


def test_generate_trip_explanation_not_found() -> None:
    missing_id = uuid.uuid4()
    mock_repo = MagicMock(spec=TripPlanRepository)
    mock_repo.get_by_id.return_value = None

    mock_service = MagicMock(spec=ExplanationService)
    mock_cache = MagicMock(spec=TripCacheManager)

    generate_trip_explanation(
        trip_id=str(missing_id),
        trip_repository=mock_repo,
        explanation_service=mock_service,
        cache_manager=mock_cache,
    )

    mock_repo.get_by_id.assert_called_once_with(missing_id)
    mock_service.explain.assert_not_called()
    mock_repo.update_explanation.assert_not_called()


def test_generate_trip_explanation_already_exists() -> None:
    trip = _make_sample_trip(has_explanation=True)
    mock_repo = MagicMock(spec=TripPlanRepository)
    mock_repo.get_by_id.return_value = trip

    mock_service = MagicMock(spec=ExplanationService)
    mock_cache = MagicMock(spec=TripCacheManager)

    generate_trip_explanation(
        trip_id=str(trip.id),
        trip_repository=mock_repo,
        explanation_service=mock_service,
        cache_manager=mock_cache,
    )

    mock_service.explain.assert_not_called()
    mock_repo.update_explanation.assert_not_called()


def test_generate_trip_explanation_service_exception_isolated() -> None:
    trip = _make_sample_trip(has_explanation=False)
    mock_repo = MagicMock(spec=TripPlanRepository)
    mock_repo.get_by_id.return_value = trip

    mock_service = MagicMock(spec=ExplanationService)
    mock_service.explain.side_effect = LLMServiceError(
        "Fireworks API rate limit exceeded"
    )

    mock_cache = MagicMock(spec=TripCacheManager)

    # Must complete cleanly without raising exception
    generate_trip_explanation(
        trip_id=str(trip.id),
        trip_repository=mock_repo,
        explanation_service=mock_service,
        cache_manager=mock_cache,
    )

    mock_service.explain.assert_called_once_with(trip)
    mock_repo.update_explanation.assert_not_called()
    mock_cache.set.assert_not_called()
