from typing import Any

from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from core.exceptions import (
    FuelRouterError,
    GeocodingUnresolvedError,
    InsufficientStationCoverageError,
    OutOfScopeLocationError,
    RoutingUnavailableError,
)


def _format_detail(data: Any) -> str:
    """Format DRF error data into a human-readable string."""
    if isinstance(data, dict):
        if "detail" in data and len(data) == 1:
            return _format_detail(data["detail"])
        parts: list[str] = []
        for field, errors in data.items():
            if isinstance(errors, list):
                msg = ", ".join(str(e) for e in errors)
            else:
                msg = str(errors)
            parts.append(f"{field}: {msg}")
        return " ".join(parts)
    if isinstance(data, list):
        return ", ".join(str(item) for item in data)
    return str(data)


def custom_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """Unified exception handler formatting errors into error and detail envelope."""
    if isinstance(exc, OutOfScopeLocationError):
        return Response(
            {"error": "out_of_scope_location", "detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, GeocodingUnresolvedError):
        return Response(
            {"error": "unresolvable_location", "detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, RoutingUnavailableError):
        return Response(
            {"error": "routing_unavailable", "detail": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if isinstance(exc, InsufficientStationCoverageError):
        return Response(
            {"error": "insufficient_station_coverage", "detail": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if isinstance(exc, FuelRouterError):
        return Response(
            {"error": "fuel_router_error", "detail": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    response = drf_exception_handler(exc, context)
    if response is not None:
        if isinstance(exc, exceptions.ValidationError):
            error_code = "invalid_request"
        elif isinstance(exc, (exceptions.NotFound, Http404)):
            error_code = "not_found"
        else:
            error_code = getattr(exc, "default_code", "error")

        detail_msg = _format_detail(response.data)
        response.data = {
            "error": error_code,
            "detail": detail_msg,
        }
        return response

    return None
