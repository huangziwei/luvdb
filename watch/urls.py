from django.urls import path, re_path

from .views import (
    CollectionCreateView,
    CollectionDetailView,
    CollectionHistoryView,
    CollectionUpdateView,
    EpisodeCreateView,
    EpisodeDetailView,
    EpisodeHistoryView,
    EpisodeUpdateView,
    GenericCheckInAllListView,
    GenericCheckInListView,
    GenreAutocomplete,
    GenreDetailView,
    MovieAutocomplete,
    MovieCastDetailView,
    MovieCreateView,
    MovieDetailView,
    MovieHistoryView,
    MovieUpdateView,
    SeasonCreateView,
    SeasonDetailView,
    SeasonHistoryView,
    SeasonUpdateView,
    SeriesAutocomplete,
    SeriesCastDetailView,
    SeriesCreateView,
    SeriesDetailView,
    SeriesHistoryView,
    SeriesUpdateView,
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
    # season
    path(
        "series/<int:series_id>/create/from/S<int:season_number>/",
        SeasonCreateView.as_view(),
        name="season_create",
    ),
    path(
        "series/<int:series_id>/S<int:season_number>/",
        SeasonDetailView.as_view(),
        name="season_detail",
    ),
    path(
        "series/<int:series_id>/S<int:season_number>/update/",
        SeasonUpdateView.as_view(),
        name="season_update",
    ),
    path(
        "series/<int:series_id>/S<int:season_number>/history/",
        SeasonHistoryView.as_view(),
        name="season_history",
    ),
    # episode
    path(
        "series/<int:series_id>/episode/create/",
        EpisodeCreateView.as_view(),
        name="episode_create",
    ),
    re_path(
        r"series/(?P<series_id>\d+)/(?P<season_episode>S\d+E\d+)/$",
        EpisodeDetailView.as_view(),
        name="episode_detail",
    ),
    re_path(
        r"series/(?P<series_id>\d+)/(?P<season_episode>S\d+E\d+)/update/$",
        EpisodeUpdateView.as_view(),
        name="episode_update",
    ),
    re_path(
        r"series/(?P<series_id>\d+)/(?P<season_episode>S\d+E\d+)/history/$",
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
        "movie/<int:object_id>/checkins/@<str:username>/",
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
        "series/<int:object_id>/checkins/@<str:username>/",
        view=GenericCheckInListView.as_view(),
        kwargs={"model_name": "series"},
        name="series_checkin_list",
    ),
    path(
        "series/<int:series_id>/S<int:season_number>/checkins/",
        view=GenericCheckInAllListView.as_view(),
        kwargs={"model_name": "season"},
        name="season_checkin_all_list",
    ),
    path(
        "series/<int:series_id>/S<int:season_number>/checkins/@<str:username>/",
        view=GenericCheckInListView.as_view(),
        kwargs={"model_name": "season"},
        name="season_checkin_list",
    ),
    # cast
    path(
        "movie/<int:pk>/cast/", MovieCastDetailView.as_view(), name="movie_cast_detail"
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
    path(
        "series-autocomplete/", SeriesAutocomplete.as_view(), name="series-autocomplete"
    ),
    path("movie-autocomplete/", MovieAutocomplete.as_view(), name="movie-autocomplete"),
]
