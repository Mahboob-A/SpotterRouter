from django.http import Http404
from rest_framework import exceptions, status

from api.exceptions import custom_exception_handler
from core.exceptions import (
    GeocodingUnresolvedError,
    InsufficientStationCoverageError,
    OutOfScopeLocationError,
    RoutingUnavailableError,
)


def test_custom_exception_handler_geocoding_unresolved() -> None:
    exc = GeocodingUnresolvedError("Could not resolve 'start' location.")
    response = custom_exception_handler(exc, {})
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "error": "unresolvable_location",
        "detail": "Could not resolve 'start' location.",
    }


def test_custom_exception_handler_out_of_scope_location() -> None:
    exc = OutOfScopeLocationError(
        "Location Honolulu, HI is outside the contiguous United States."
    )
    response = custom_exception_handler(exc, {})
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "error": "out_of_scope_location",
        "detail": "Location Honolulu, HI is outside the contiguous United States.",
    }


def test_custom_exception_handler_routing_unavailable() -> None:
    exc = RoutingUnavailableError("The routing service did not respond.")
    response = custom_exception_handler(exc, {})
    assert response is not None
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.data == {
        "error": "routing_unavailable",
        "detail": "The routing service did not respond.",
    }


def test_custom_exception_handler_insufficient_station_coverage() -> None:
    exc = InsufficientStationCoverageError(
        "No fuel station reachable within vehicle range."
    )
    response = custom_exception_handler(exc, {})
    assert response is not None
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.data == {
        "error": "insufficient_station_coverage",
        "detail": "No fuel station reachable within vehicle range.",
    }


def test_custom_exception_handler_not_found() -> None:
    exc = exceptions.NotFound("Trip plan with the specified ID was not found.")
    response = custom_exception_handler(exc, {})
    assert response is not None
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == {
        "error": "not_found",
        "detail": "Trip plan with the specified ID was not found.",
    }


def test_custom_exception_handler_http404() -> None:
    exc = Http404("Trip plan does not exist.")
    response = custom_exception_handler(exc, {})
    assert response is not None
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == {
        "error": "not_found",
        "detail": "Trip plan does not exist.",
    }


def test_custom_exception_handler_validation_error() -> None:
    exc = exceptions.ValidationError({"start": ["This field may not be blank."]})
    response = custom_exception_handler(exc, {})
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "error": "invalid_request",
        "detail": "start: This field may not be blank.",
    }


def test_custom_exception_handler_method_not_allowed() -> None:
    exc = exceptions.MethodNotAllowed("PUT")
    response = custom_exception_handler(exc, {})
    assert response is not None
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert "error" in response.data
    assert "detail" in response.data
