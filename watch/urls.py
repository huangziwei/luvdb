from django.urls import path

from .views import (
    MovieCastDetailView,
    MovieCreateView,
    MovieDetailView,
    MovieUpdateView,
    SeriesCreateView,
    SeriesDetailView,
    SeriesUpdateView,
    StudioAutocomplete,
    StudioCreateView,
    StudioDetailView,
    WatchListView,
)

app_name = "watch"
urlpatterns = [
    # play
    path("recent/", WatchListView.as_view(), name="watch_list"),
    # movie
    path("movie/create/", MovieCreateView.as_view(), name="movie_create"),
    path("movie/<int:pk>/", MovieDetailView.as_view(), name="movie_detail"),
    path("movie/<int:pk>/update/", MovieUpdateView.as_view(), name="movie_update"),
    # series
    path("series/create/", SeriesCreateView.as_view(), name="series_create"),
    path("series/<int:pk>/", SeriesDetailView.as_view(), name="series_detail"),
    path("series/<int:pk>/update/", SeriesUpdateView.as_view(), name="series_update"),
    # studio
    path("studio/create/", StudioCreateView.as_view(), name="studio_create"),
    path("studio/<int:pk>/", StudioDetailView.as_view(), name="studio_detail"),
    # autocomplete
    path(
        "studio-autocomplete/",
        StudioAutocomplete.as_view(),
        name="studio-autocomplete",
    ),
    # # checkin
    # path(
    #     "movie/<int:movie_id>/checkins/",
    #     view=MovieCheckInAllListView.as_view(),
    #     name="movie_checkin_all_list",
    # ),
    # path(
    #     "movie/<int:movie_id>/<str:username>/checkins/",
    #     view=MovieCheckInListView.as_view(),
    #     name="movie_checkin_list",
    # ),
    # path(
    #     "checkin/<int:pk>/",
    #     MovieCheckInDetailView.as_view(),
    #     name="movie_checkin_detail",
    # ),
    # path(
    #     "checkin/<int:pk>/update/",
    #     MovieCheckInUpdateView.as_view(),
    #     name="movie_checkin_update",
    # ),
    # path(
    #     "checkin/<int:pk>/delete/",
    #     MovieCheckInDeleteView.as_view(),
    #     name="movie_checkin_delete",
    # ),
    # # series
    # path("series/create/", MovieSeriesCreateView.as_view(), name="series_create"),
    # path("series/<int:pk>/", MovieSeriesDetailView.as_view(), name="series_detail"),
    # path(
    #     "series/<int:pk>/update/", MovieSeriesUpdateView.as_view(), name="series_update"
    # ),
    # cast
    path(
        "movie/<int:pk>/cast/", MovieCastDetailView.as_view(), name="movie_cast_detail"
    ),
]
