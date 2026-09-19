from django.urls import path

from ui.views import (
    DatasetsView,
    DocsView,
    HomeView,
    LocationsView,
    RecentTripsApiView,
    TripDetailView,
    TripPdfView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path(
        "trips/<uuid:trip_id>/",
        TripDetailView.as_view(),
        name="trip-detail",
    ),
    path(
        "trips/<uuid:trip_id>/pdf/",
        TripPdfView.as_view(),
        name="trip-pdf",
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
    path(
        "docs/",
        DocsView.as_view(),
        name="docs",
    ),
]
