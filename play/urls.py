from django.urls import path

from .views import (
    DLCCreateView,
    DLCDetailView,
    DLCHistoryView,
    DLCUpdateView,
    GameAutocomplete,
    GameCastDetailView,
    GameCreateView,
    GameDetailView,
    GameHistoryView,
    GameSeriesCreateView,
    GameSeriesDetailView,
    GameSeriesHistoryView,
    GameSeriesUpdateView,
    GameUpdateView,
    GenreAutocomplete,
    GenreDetailView,
    PlatformAutocomplete,
    PlatformCreateView,
    PlatformDetailView,
    PlatformHistoryView,
    PlatformUpdateView,
    PlayCheckInAllListView,
    PlayCheckInDeleteView,
    PlayCheckInDetailView,
    PlayCheckInListView,
    PlayCheckInUpdateView,
    PlayCheckInUserListView,
    PlayListAllView,
    PlayListView,
    WorkAutocomplete,
    WorkCreateView,
    WorkDetailView,
    WorkHistoryView,
    WorkUpdateView,
)

app_name = "play"
urlpatterns = [
    # play
    path("recent/", PlayListView.as_view(), name="play_list"),
    path("all/", PlayListAllView.as_view(), name="play_list_all"),
    # work
    path("work/create/", WorkCreateView.as_view(), name="work_create"),
    path("work/<int:pk>/", WorkDetailView.as_view(), name="work_detail"),
    path("work/<int:pk>/update/", WorkUpdateView.as_view(), name="work_update"),
    path("work/<int:pk>/history/", WorkHistoryView.as_view(), name="work_history"),
    # game
    path("game/create/", GameCreateView.as_view(), name="game_create"),
    path(
        "game/create/<int:work_id>/",
        GameCreateView.as_view(),
        name="game_create_with_work",
    ),
    path("game/<int:pk>/", GameDetailView.as_view(), name="game_detail"),
    path("game/<int:pk>/update/", GameUpdateView.as_view(), name="game_update"),
    path("game/<int:pk>/history/", GameHistoryView.as_view(), name="game_history"),
    # dlc
    path("game/<int:game_id>/dlc/create/", DLCCreateView.as_view(), name="dlc_create"),
    path(
        "game/<int:game_id>/dlc/<int:pk>/", DLCDetailView.as_view(), name="dlc_detail"
    ),
    path(
        "game/<int:game_id>/dlc/<int:pk>/update/",
        DLCUpdateView.as_view(),
        name="dlc_update",
    ),
    path(
        "game/<int:game_id>/dlc/<int:pk>/history/",
        DLCHistoryView.as_view(),
        name="dlc_history",
    ),
    # platform
    path("platform/create/", PlatformCreateView.as_view(), name="platform_create"),
    path("platform/<int:pk>/", PlatformDetailView.as_view(), name="platform_detail"),
    path(
        "platform/<int:pk>/update/",
        PlatformUpdateView.as_view(),
        name="platform_update",
    ),
    path(
        "platform/<int:pk>/history/",
        PlatformHistoryView.as_view(),
        name="platform_history",
    ),
    # autocomplete
    path(
        "platform-autocomplete/",
        PlatformAutocomplete.as_view(),
        name="platform-autocomplete",
    ),
    path("work-autocomplete/", WorkAutocomplete.as_view(), name="work-autocomplete"),
    path("game-autocomplete/", GameAutocomplete.as_view(), name="game-autocomplete"),
    path("genre-autocomplete/", GenreAutocomplete.as_view(), name="genre-autocomplete"),
    # checkin
    path(
        "game/<int:object_id>/checkins/",
        view=PlayCheckInAllListView.as_view(),
        name="play_checkin_all_list",
    ),
    path(
        "game/<int:object_id>/checkins/@<str:username>/",
        view=PlayCheckInListView.as_view(),
        name="play_checkin_list",
    ),
    # cast
    path("game/<int:pk>/cast/", GameCastDetailView.as_view(), name="game_cast_detail"),
    # series
    path("series/create/", GameSeriesCreateView.as_view(), name="series_create"),
    path("series/<int:pk>/", GameSeriesDetailView.as_view(), name="series_detail"),
    path(
        "series/<int:pk>/update/", GameSeriesUpdateView.as_view(), name="series_update"
    ),
    path(
        "series/<int:pk>/history/",
        GameSeriesHistoryView.as_view(),
        name="series_history",
    ),
    # genre
    path("genre/<slug:slug>/", GenreDetailView.as_view(), name="genre_detail"),
]
