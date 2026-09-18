from django.urls import path

from ui.views import HomeView, TripDetailView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path(
        "trips/<uuid:trip_id>/",
        TripDetailView.as_view(),
        name="trip-detail",
    ),
]
