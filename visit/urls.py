from django.urls import path

from .views import (
    LocationAutoComplete,
    LocationCreateView,
    LocationDetailView,
    LocationHistoryView,
    LocationListView,
    LocationUpdateView,
)

app_name = "visit"
urlpatterns = [
    path("location/create/", LocationCreateView.as_view(), name="location_create"),
    path("location/<int:pk>/", LocationDetailView.as_view(), name="location_detail"),
    path(
        "location/<int:pk>/update/",
        LocationUpdateView.as_view(),
        name="location_update",
    ),
    path(
        "location/<int:pk>/history/",
        LocationHistoryView.as_view(),
        name="location_history",
    ),
    path("location/", LocationListView.as_view(), name="location_list"),
    path(
        "location-autocomplete/",
        LocationAutoComplete.as_view(),
        name="location-autocomplete",
    ),
]
