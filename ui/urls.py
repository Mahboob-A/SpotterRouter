from django.urls import path

from ui.views import (
    DatasetsView,
    HomeView,
    LocationsView,
    RecentTripsApiView,
    TripDetailView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path(
        "trips/<uuid:trip_id>/",
        TripDetailView.as_view(),
        name="trip-detail",
    ),
    path(
        "recent-trips/",
        RecentTripsApiView.as_view(),
        name="recent-trips",
    ),
    path(
        "locations/",
        LocationsView.as_view(),
        name="locations",
    ),
    path(
        "datasets/",
        DatasetsView.as_view(),
        name="datasets",
    ),
]
