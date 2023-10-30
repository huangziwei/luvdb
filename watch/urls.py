from django.urls import path

from .views import (
    CollectionCreateView,
    CollectionDetailView,
    CollectionHistoryView,
    CollectionUpdateView,
    EpisodeCastDetailView,
    EpisodeCreateView,
    EpisodeDetailView,
    EpisodeHistoryView,
    EpisodeUpdateView,
    GenericCheckInAllListView,
    GenericCheckInListView,
    GenericCheckInUserListView,
    GenreAutocomplete,
    GenreDetailView,
    MovieCastDetailView,
    MovieCreateView,
    MovieDetailView,
    MovieHistoryView,
    MovieUpdateView,
    SeriesCastDetailView,
    SeriesCreateView,
    SeriesDetailView,
    SeriesHistoryView,
    SeriesUpdateView,
    WatchCheckInCreateView,
    WatchCheckInDeleteView,
    WatchCheckInDetailView,
    WatchCheckInUpdateView,
    WatchListAllView,
    WatchListView,
)

app_name = "watch"
urlpatterns = [
    # play
    path("recent/", WatchListView.as_view(), name="watch_list"),
    path("all/", WatchListAllView.as_view(), name="watch_list_all"),
    # movie
    path("movie/create/", MovieCreateView.as_view(), name="movie_create"),
    path(
        "movie/<int:pk>/",
        MovieDetailView.as_view(),
        kwargs={"model_name": "movie"},
        name="movie_detail",
    ),
    path("movie/<int:pk>/update/", MovieUpdateView.as_view(), name="movie_update"),
    path("movie/<int:pk>/history/", MovieHistoryView.as_view(), name="movie_history"),
    # series
    path("series/create/", SeriesCreateView.as_view(), name="series_create"),
    path(
        "series/<int:pk>/",
        SeriesDetailView.as_view(),
        kwargs={"model_name": "series"},
        name="series_detail",
    ),
    path("series/<int:pk>/update/", SeriesUpdateView.as_view(), name="series_update"),
    path(
        "series/<int:pk>/history/", SeriesHistoryView.as_view(), name="series_history"
    ),
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
    path(
        "series/<int:series_id>/episode/<int:pk>/history/",
        EpisodeHistoryView.as_view(),
        name="episode_history",
    ),
    # autocomplete
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
    # collection
    path(
        "collection/create/", CollectionCreateView.as_view(), name="collection_create"
    ),
    path(
        "collection/<int:pk>/",
        CollectionDetailView.as_view(),
        name="collection_detail",
    ),
    path(
        "collection/<int:pk>/update/",
        CollectionUpdateView.as_view(),
        name="collection_update",
    ),
    path(
        "collection/<int:pk>/history/",
        CollectionHistoryView.as_view(),
        name="collection_history",
    ),
]
