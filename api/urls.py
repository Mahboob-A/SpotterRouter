from django.urls import path

from api.views import HealthCheckView, TripPlanDetailView, TripPlanView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("trips/", TripPlanView.as_view(), name="trip-plan-list-create"),
    path(
        "trips/<uuid:trip_id>/",
        TripPlanDetailView.as_view(),
        name="trip-plan-detail",
    ),
]
