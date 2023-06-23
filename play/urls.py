from django.urls import path

from .views import (
    DeveloperAutocomplete,
    DeveloperCreateView,
    DeveloperDetailView,
    GameCheckInAllListView,
    GameCheckInDetailView,
    GameCheckInListView,
    GameCreateView,
    GameDetailView,
    GameUpdateView,
    PlatformAutocomplete,
    PlatformCreateView,
    PlatformDetailView,
    PlayListView,
)

app_name = "play"
urlpatterns = [
    # play
    path("recent/", PlayListView.as_view(), name="play_list"),
    # game
    path("game/create/", GameCreateView.as_view(), name="game_create"),
    path("game/<int:pk>/", GameDetailView.as_view(), name="game_detail"),
    path("game/<int:pk>/update/", GameUpdateView.as_view(), name="game_update"),
    # developer
    path("developer/create/", DeveloperCreateView.as_view(), name="developer_create"),
    path("developer/<int:pk>/", DeveloperDetailView.as_view(), name="developer_detail"),
    # platform
    path("platform/create/", PlatformCreateView.as_view(), name="platform_create"),
    path("platform/<int:pk>/", PlatformDetailView.as_view(), name="platform_detail"),
    path(
        "checkin/<int:pk>/", GameCheckInDetailView.as_view(), name="game_checkin_detail"
    ),
    # path(
    #     "checkin/<int:pk>/update/",
    #     BookCheckInUpdateView.as_view(),
    #     name="book_checkin_update",
    # ),
    # path(
    #     "checkin/<int:pk>/delete/",
    #     BookCheckInDeleteView.as_view(),
    #     name="book_checkin_delete",
    # ),
    # autocomplete
    path(
        "developer-autocomplete/",
        DeveloperAutocomplete.as_view(),
        name="developer-autocomplete",
    ),
    path(
        "platform-autocomplete/",
        PlatformAutocomplete.as_view(),
        name="platform-autocomplete",
    ),
    # checkin
    path(
        "game/<int:game_id>/checkins/",
        view=GameCheckInAllListView.as_view(),
        name="game_checkin_all_list",
    ),
    path(
        "game/<int:game_id>/<str:username>/checkins/",
        view=GameCheckInListView.as_view(),
        name="game_checkin_list",
    ),
]
