from django.urls import path

from .views import (
    LabelAutocomplete,
    LabelCreateView,
    LabelDetailView,
    ListenCheckInAllListView,
    ListenCheckInDeleteView,
    ListenCheckInDetailView,
    ListenCheckInListView,
    ListenCheckInUpdateView,
    ListenCheckInUserListView,
    ListenListView,
    ReleaseCreateView,
    ReleaseDetailView,
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
        "release/<int:release_id>/checkins/",
        view=ListenCheckInAllListView.as_view(),
        name="listen_checkin_all_list",
    ),
    path(
        "release/<int:release_id>/<str:username>/checkins/",
        view=ListenCheckInListView.as_view(),
        name="listen_checkin_list",
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
]
