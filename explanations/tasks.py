"""Celery background tasks for generating AI trip explanations."""

import logging
import os
import uuid

from celery import shared_task
from django.conf import settings

from explanations.exceptions import LLMConfigurationError
from explanations.services import ExplanationService
from trips.caching import TripCacheManager
from trips.repositories import TripPlanRepository

logger = logging.getLogger(__name__)

UNCONFIGURED_EXPLANATION_NOTICE = (
    "Analysis is unconfigured: FIREWORKS_API_KEY is not set in this "
    "environment. To enable real-time AI-powered route analysis, supply a valid "
    "Fireworks API key in your environment configuration."
)


@shared_task(name="explanations.tasks.generate_trip_explanation")  # type: ignore[untyped-decorator]
def generate_trip_explanation(
    trip_id: str,
    trip_repository: TripPlanRepository | None = None,
    explanation_service: ExplanationService | None = None,
    cache_manager: TripCacheManager | None = None,
) -> None:
    """Asynchronously generate a plain-language explanation and attach to TripPlan."""
    repo = trip_repository or TripPlanRepository()
    service = explanation_service or ExplanationService()
    cache = cache_manager or TripCacheManager()

    try:
        try:
            parsed_id = uuid.UUID(trip_id)
        except (ValueError, TypeError, AttributeError) as parse_err:
            logger.warning(
                "Invalid trip_id format received: %s (%s)", trip_id, parse_err
            )
            return

        trip_plan = repo.get_by_id(parsed_id)
        if trip_plan is None:
            logger.warning(
                "TripPlan with id %s not found for explanation generation",
                trip_id,
            )
            return

        if trip_plan.ai_explanation:
            logger.info(
                "TripPlan %s already has an ai_explanation; skipping generation",
                trip_id,
            )
            return

        configured_key = getattr(
            settings,
            "FIREWORKS_API_KEY",
            os.environ.get("FIREWORKS_API_KEY", ""),
        )
        if not configured_key or not str(configured_key).strip():
            logger.info(
                "FIREWORKS_API_KEY is not configured; "
                "setting informative notice for trip %s",
                trip_id,
            )
            repo.update_explanation(trip_plan.id, UNCONFIGURED_EXPLANATION_NOTICE)
            trip_plan.ai_explanation = UNCONFIGURED_EXPLANATION_NOTICE
            cache.set(trip_plan)
            return

        try:
            explanation = service.explain(trip_plan)
        except LLMConfigurationError:
            logger.info(
                "LLM configuration error for trip %s; setting informative notice",
                trip_id,
            )
            repo.update_explanation(trip_plan.id, UNCONFIGURED_EXPLANATION_NOTICE)
            trip_plan.ai_explanation = UNCONFIGURED_EXPLANATION_NOTICE
            cache.set(trip_plan)
            return
        except Exception as llm_err:
            logger.warning(
                "LLM explanation generation failed for trip %s (%s); applying fallback",
                trip_id,
                llm_err,
            )
            explanation = service.build_fallback_explanation(trip_plan)

        if not explanation or not explanation.strip():
            logger.warning(
                "ExplanationService returned empty explanation for trip %s; applying fallback",
                trip_id,
            )
            explanation = service.build_fallback_explanation(trip_plan)

        cleaned = explanation.strip()
        repo.update_explanation(trip_plan.id, cleaned)

        # Synchronize in-memory model and update Redis cache
        trip_plan.ai_explanation = cleaned
        cache.set(trip_plan)
        logger.info("Successfully attached AI explanation to trip %s", trip_id)

    except Exception as exc:
        # Fault isolation per Rule 10: failures are logged and never retried.
        logger.exception(
            "Failed to generate AI explanation for trip %s: %s",
            trip_id,
            exc,
        )
