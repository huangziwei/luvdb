from django.urls import path

from .views import (
    EpisodeCastDetailView,
    EpisodeCreateView,
    EpisodeDetailView,
    EpisodeUpdateView,
    GenericCheckInAllListView,
    GenericCheckInListView,
    GenericCheckInUserListView,
    GenreAutocomplete,
    GenreDetailView,
    MovieCastDetailView,
    MovieCreateView,
    MovieDetailView,
    MovieUpdateView,
    SeriesCastDetailView,
    SeriesCreateView,
    SeriesDetailView,
    SeriesUpdateView,
    StudioAutocomplete,
    StudioCreateView,
    StudioDetailView,
    StudioUpdateView,
    WatchCheckInCreateView,
    WatchCheckInDeleteView,
    WatchCheckInDetailView,
    WatchCheckInUpdateView,
    WatchListView,
)

app_name = "watch"
urlpatterns = [
    # play
    path("recent/", WatchListView.as_view(), name="watch_list"),
    # movie
    path("movie/create/", MovieCreateView.as_view(), name="movie_create"),
    path(
        "movie/<int:pk>/",
        MovieDetailView.as_view(),
        kwargs={"model_name": "movie"},
        name="movie_detail",
    ),
    path("movie/<int:pk>/update/", MovieUpdateView.as_view(), name="movie_update"),
    # series
    path("series/create/", SeriesCreateView.as_view(), name="series_create"),
    path(
        "series/<int:pk>/",
        SeriesDetailView.as_view(),
        kwargs={"model_name": "series"},
        name="series_detail",
    ),
    path("series/<int:pk>/update/", SeriesUpdateView.as_view(), name="series_update"),
    # episode
    path(
        "series/<int:series_id>/episode/create/",
        EpisodeCreateView.as_view(),
        name="episode_create",
    ),
    path(
        "series/<int:series_id>/episode/<int:pk>/",
        EpisodeDetailView.as_view(),
        name="episode_detail",
    ),
    path(
        "series/<int:series_id>/episode/<int:pk>/update/",
        EpisodeUpdateView.as_view(),
        name="episode_update",
    ),
    # studio
    path("studio/create/", StudioCreateView.as_view(), name="studio_create"),
    path("studio/<int:pk>/", StudioDetailView.as_view(), name="studio_detail"),
    path("studio/<int:pk>/update/", StudioUpdateView.as_view(), name="studio_update"),
    # autocomplete
    path(
        "studio-autocomplete/",
        StudioAutocomplete.as_view(),
        name="studio-autocomplete",
    ),
    path("genre-autocomplete/", GenreAutocomplete.as_view(), name="genre-autocomplete"),
    # checkin
    path(
        "movie/<int:object_id>/checkins/",
        view=GenericCheckInAllListView.as_view(),
        kwargs={"model_name": "movie"},
        name="movie_checkin_all_list",
    ),
    path(
        "movie/<int:object_id>/<str:username>/checkins/",
        view=GenericCheckInListView.as_view(),
        kwargs={"model_name": "movie"},
        name="movie_checkin_list",
    ),
    path(
        "series/<int:object_id>/checkins/",
        view=GenericCheckInAllListView.as_view(),
        kwargs={"model_name": "series"},
        name="series_checkin_all_list",
    ),
    path(
        "series/<int:object_id>/<str:username>/checkins/",
        view=GenericCheckInListView.as_view(),
        kwargs={"model_name": "series"},
        name="series_checkin_list",
    ),
    path(
        "checkin/<int:pk>/",
        WatchCheckInDetailView.as_view(),
        name="watch_checkin_detail",
    ),
    path(
        "checkin/<int:pk>/update/",
        WatchCheckInUpdateView.as_view(),
        name="watch_checkin_update",
    ),
    path(
        "checkin/<int:pk>/delete/",
        WatchCheckInDeleteView.as_view(),
        name="watch_checkin_delete",
    ),
    path(
        "<str:username>/checkins/",
        GenericCheckInUserListView.as_view(),
        name="watch_checkin_user_list",
    ),
    # cast
    path(
        "movie/<int:pk>/cast/", MovieCastDetailView.as_view(), name="movie_cast_detail"
    ),
    # episode cast
    path(
        "series/<int:series_id>/episode/<int:pk>/cast/",
        EpisodeCastDetailView.as_view(),
        name="episode_cast_detail",
    ),
    # series cast
    path(
        "series/<int:pk>/cast/",
        SeriesCastDetailView.as_view(),
        name="series_cast_detail",
    ),
    # genre
    path("genre/<slug:name>/", GenreDetailView.as_view(), name="genre_detail"),
]
