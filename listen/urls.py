from django.urls import path

from .views import (
    AudiobookCreateView,
    AudiobookDetailView,
    AudiobookHistoryView,
    AudiobookUpdateView,
    GenericCheckInAllListView,
    GenericCheckInListView,
    GenreAutocomplete,
    GenreDetailView,
    ListenListAllView,
    ListenListView,
    PodcastCreateView,
    PodcastDetailView,
    PodcastUpdateView,
    ReleaseCreateView,
    ReleaseCreditDetailView,
    ReleaseDetailView,
    ReleaseGroupCreateView,
    ReleaseGroupDetailView,
    ReleaseGroupHistoryView,
    ReleaseGroupUpdateView,
    ReleaseHistoryView,
    ReleaseUpdateView,
    TrackAutocomplete,
    TrackCreateView,
    TrackDetailView,
    TrackHistoryView,
    TrackUpdateView,
    WorkAutocomplete,
    WorkCreateView,
    WorkDetailView,
    WorkHistoryView,
    WorkUpdateView,
)

app_name = "listen"
urlpatterns = [
    # work
    path("work/create/", WorkCreateView.as_view(), name="work_create"),
    path("work/<int:pk>/", WorkDetailView.as_view(), name="work_detail"),
    path("work/<int:pk>/update/", WorkUpdateView.as_view(), name="work_update"),
    path("work/<int:pk>/history/", WorkHistoryView.as_view(), name="work_history"),
    # track
    path("track/create/", TrackCreateView.as_view(), name="track_create"),
    path("track/<int:pk>/", TrackDetailView.as_view(), name="track_detail"),
    path("track/<int:pk>/update/", TrackUpdateView.as_view(), name="track_update"),
    path("track/<int:pk>/history/", TrackHistoryView.as_view(), name="track_history"),
    # release
    path("release/create/", ReleaseCreateView.as_view(), name="release_create"),
    path("release/<int:pk>/", ReleaseDetailView.as_view(), name="release_detail"),
    path(
        "release/<int:pk>/update/", ReleaseUpdateView.as_view(), name="release_update"
    ),
    path(
        "release/<int:pk>/credits/",
        ReleaseCreditDetailView.as_view(),
        name="release_credit",
    ),
    path(
        "release/<int:pk>/history/",
        ReleaseHistoryView.as_view(),
        name="release_history",
    ),
    # podcast
    path("podcast/create/", PodcastCreateView.as_view(), name="podcast_create"),
    path("podcast/<int:pk>/", PodcastDetailView.as_view(), name="podcast_detail"),
    path(
        "podcast/<int:pk>/update/", PodcastUpdateView.as_view(), name="podcast_update"
    ),
    path("work-autocomplete/", WorkAutocomplete.as_view(), name="work-autocomplete"),
    path("track-autocomplete/", TrackAutocomplete.as_view(), name="track-autocomplete"),
    # checkin
    path(
        "release/<int:object_id>/checkins/",
        view=GenericCheckInAllListView.as_view(),
        kwargs={"model_name": "release"},
        name="release_checkin_all_list",
    ),
    path(
        "release/<int:object_id>/checkins/@<str:username>/",
        view=GenericCheckInListView.as_view(),
        kwargs={"model_name": "release"},
        name="release_checkin_list",
    ),
    path(
        "podcast/<int:object_id>/checkins/",
        view=GenericCheckInAllListView.as_view(),
        kwargs={"model_name": "podcast"},
        name="podcast_checkin_all_list",
    ),
    path(
        "podcast/<int:object_id>/checkins/@<str:username>/",
        view=GenericCheckInListView.as_view(),
        kwargs={"model_name": "podcast"},
        name="podcast_checkin_list",
    ),
    path(
        "audiobook/<int:object_id>/checkins/",
        view=GenericCheckInAllListView.as_view(),
        kwargs={"model_name": "audiobook"},
        name="audiobook_checkin_all_list",
    ),
    path(
        "audiobook/<int:object_id>/checkins/@<str:username>/",
        view=GenericCheckInListView.as_view(),
        kwargs={"model_name": "audiobook"},
        name="audiobook_checkin_list",
    ),
    # recent
    path("recent/", ListenListView.as_view(), name="listen_list"),
    path("all/", ListenListAllView.as_view(), name="listen_list_all"),
    # genre
    path("genre/<slug:slug>/", GenreDetailView.as_view(), name="genre_detail"),
    path("genre-autocomplete/", GenreAutocomplete.as_view(), name="genre-autocomplete"),
    # release group
    path(
        "releasegroup/create/",
        ReleaseGroupCreateView.as_view(),
        name="releasegroup_create",
    ),
    path(
        "releasegroup/<int:pk>/",
        ReleaseGroupDetailView.as_view(),
        name="releasegroup_detail",
    ),
    path(
        "releasegroup/<int:pk>/update/",
        ReleaseGroupUpdateView.as_view(),
        name="releasegroup_update",
    ),
    path(
        "releasegroup/<int:pk>/history/",
        ReleaseGroupHistoryView.as_view(),
        name="releasegroup_history",
    ),
    # audiobook
    path("audiobook/create/", AudiobookCreateView.as_view(), name="audiobook_create"),
    path("audiobook/<int:pk>/", AudiobookDetailView.as_view(), name="audiobook_detail"),
    path(
        "audiobook/<int:pk>/update/",
        AudiobookUpdateView.as_view(),
        name="audiobook_update",
    ),
    path(
        "audiobook/<int:pk>/history/",
        AudiobookHistoryView.as_view(),
        name="audiobook_history",
    ),
]
