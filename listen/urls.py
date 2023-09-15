from django.urls import path

from .views import (
    AudiobookCreateView,
    AudiobookDetailView,
    AudiobookUpdateView,
    GenericCheckInAllListView,
    GenericCheckInListView,
    GenreAutocomplete,
    GenreDetailView,
    LabelAutocomplete,
    LabelCreateView,
    LabelDetailView,
    LabelUpdateView,
    ListenCheckInDeleteView,
    ListenCheckInDetailView,
    ListenCheckInUpdateView,
    ListenCheckInUserListView,
    ListenListView,
    PodcastCreateView,
    PodcastDetailView,
    PodcastUpdateView,
    ReleaseCreateView,
    ReleaseDetailView,
    ReleaseGroupCreateView,
    ReleaseGroupDetailView,
    ReleaseGroupUpdateView,
    ReleaseUpdateView,
    TrackAutocomplete,
    TrackCreateView,
    TrackDetailView,
    TrackUpdateView,
    WorkAutocomplete,
    WorkCreateView,
    WorkDetailView,
    WorkUpdateView,
)

app_name = "listen"
urlpatterns = [
    # label
    path("label/create/", LabelCreateView.as_view(), name="label_create"),
    path("label/<int:pk>/", LabelDetailView.as_view(), name="label_detail"),
    path("label/<int:pk>/update/", LabelUpdateView.as_view(), name="label_update"),
    # work
    path("work/create/", WorkCreateView.as_view(), name="work_create"),
    path("work/<int:pk>/", WorkDetailView.as_view(), name="work_detail"),
    path("work/<int:pk>/update/", WorkUpdateView.as_view(), name="work_update"),
    # track
    path("track/create/", TrackCreateView.as_view(), name="track_create"),
    path("track/<int:pk>/", TrackDetailView.as_view(), name="track_detail"),
    path("track/<int:pk>/update/", TrackUpdateView.as_view(), name="track_update"),
    # release
    path("release/create/", ReleaseCreateView.as_view(), name="release_create"),
    path("release/<int:pk>/", ReleaseDetailView.as_view(), name="release_detail"),
    path(
        "release/<int:pk>/update/", ReleaseUpdateView.as_view(), name="release_update"
    ),
    # podcast
    path("podcast/create/", PodcastCreateView.as_view(), name="podcast_create"),
    path("podcast/<int:pk>/", PodcastDetailView.as_view(), name="podcast_detail"),
    path(
        "podcast/<int:pk>/update/", PodcastUpdateView.as_view(), name="podcast_update"
    ),
    # autocomplete views
    path(
        "label-autocomplete/",
        LabelAutocomplete.as_view(),
        name="label-autocomplete",
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
        "release/<int:object_id>/<str:username>/checkins/",
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
        "podcast/<int:object_id>/<str:username>/checkins/",
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
        "audiobook/<int:object_id>/<str:username>/checkins/",
        view=GenericCheckInListView.as_view(),
        kwargs={"model_name": "audiobook"},
        name="audiobook_checkin_list",
    ),
    path(
        "checkin/<int:pk>/",
        ListenCheckInDetailView.as_view(),
        name="listen_checkin_detail",
    ),
    path(
        "checkin/<int:pk>/update/",
        ListenCheckInUpdateView.as_view(),
        name="listen_checkin_update",
    ),
    path(
        "checkin/<int:pk>/delete/",
        ListenCheckInDeleteView.as_view(),
        name="listen_checkin_delete",
    ),
    path(
        "<str:username>/checkins/",
        ListenCheckInUserListView.as_view(),
        name="listen_checkin_user_list",
    ),
    # recent
    path("recent/", ListenListView.as_view(), name="listen_list"),
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
    # audiobook
    path("audiobook/create/", AudiobookCreateView.as_view(), name="audiobook_create"),
    path("audiobook/<int:pk>/", AudiobookDetailView.as_view(), name="audiobook_detail"),
    path(
        "audiobook/<int:pk>/update/",
        AudiobookUpdateView.as_view(),
        name="audiobook_update",
    ),
]
