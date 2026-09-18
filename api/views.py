from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):  # type: ignore[misc]
    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    def get(self, request: object) -> Response:
        return Response({"status": "ok"})
