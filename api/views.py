import uuid
from typing import Any

from rest_framework import exceptions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import (
    TripPlanListSerializer,
    TripPlanRequestSerializer,
    TripPlanResponseSerializer,
)
from trips.repositories import TripPlanRepository
from trips.services import TripPlanningService


class HealthCheckView(APIView):  # type: ignore[misc]
    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class TripPlanView(APIView):  # type: ignore[misc]
    """API endpoint for creating optimal trip plans and listing past trips."""

    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    def __init__(
        self,
        service: TripPlanningService | None = None,
        repository: TripPlanRepository | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._service = service or TripPlanningService()
        self._repository = repository or TripPlanRepository()

    def post(self, request: Request) -> Response:
        serializer = TripPlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = self._service.plan_trip(
            start_input=serializer.validated_data["start"],
            end_input=serializer.validated_data["end"],
        )
        response_serializer = TripPlanResponseSerializer(plan)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def get(self, request: Request) -> Response:
        trips = self._repository.list_recent(limit=50)
        response_serializer = TripPlanListSerializer(trips, many=True)
        return Response(
            {"results": response_serializer.data},
            status=status.HTTP_200_OK,
        )


class TripPlanDetailView(APIView):  # type: ignore[misc]
    """API endpoint for retrieving a single trip plan detail."""

    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    def __init__(
        self,
        repository: TripPlanRepository | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._repository = repository or TripPlanRepository()

    def get(self, request: Request, trip_id: uuid.UUID) -> Response:
        trip = self._repository.get_by_id(trip_id)
        if trip is None:
            raise exceptions.NotFound(
                "Trip plan with the specified ID was not found."
            )
        response_serializer = TripPlanResponseSerializer(trip)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
