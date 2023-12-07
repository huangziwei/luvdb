from django.urls import path, re_path

from listen.views import GenericCheckInUserListView as GenericListenCheckInUserListView
from listen.views import (
    ListenCheckInDeleteView,
    ListenCheckInDetailView,
    ListenCheckInUpdateView,
)
from play.views import (
    PlayCheckInDeleteView,
    PlayCheckInDetailView,
    PlayCheckInUpdateView,
    PlayCheckInUserListView,
)
from read.views import GenericCheckInUserListView as GenericReadCheckInUserListView
from read.views import (
    ReadCheckInDeleteView,
    ReadCheckInDetailView,
    ReadCheckInUpdateView,
)
from watch.views import GenericCheckInUserListView as GenericWatchCheckInUserListView
from watch.views import (
    WatchCheckInDeleteView,
    WatchCheckInDetailView,
    WatchCheckInUpdateView,
)

from .feeds import (
    TagListFeed,
    TagUserListFeed,
    UserPinFeed,
    UserPostFeed,
    UserPostProjectFeed,
    UserSayFeed,
)
from .views import (
    CommentCreateView,
    CommentDeleteView,
    CommentListView,
    CommentUpdateView,
    LuvListCreateView,
    LuvListDeleteView,
    LuvListDetailView,
    LuvListUpdateView,
    LuvListUserListView,
    PinCreateView,
    PinDeleteView,
    PinDetailView,
    PinListView,
    PinsFromURLView,
    PinUpdateView,
    PostCreateView,
    PostDeleteView,
    PostDetailView,
    PostListView,
    PostUpdateView,
    ProjectAutocomplete,
    ProjectUpdateView,
    RandomizerDetailView,
    RepostCreateView,
    RepostDeleteView,
    RepostDetailView,
    RepostUpdateView,
    SayCreateView,
    SayDeleteView,
    SayDetailView,
    SayListView,
    SayUpdateView,
    TagListView,
    TagUserListView,
)

app_name = "write"
urlpatterns = [
    # pin
    path("@<str:username>/pins/", PinListView.as_view(), name="pin_list"),
    path("@<str:username>/pins/rss/", UserPinFeed(), name="user_pin_feed"),
    re_path(
        r"^pins/from/(?P<root_url>.+)/$",
        PinsFromURLView.as_view(),
        name="pins_from_url",
    ),
    path("@<str:username>/pin/create/", PinCreateView.as_view(), name="pin_create"),
    path("@<str:username>/pin/<int:pk>/", PinDetailView.as_view(), name="pin_detail"),
    path(
        "@<str:username>/pin/<int:pk>/update/",
        PinUpdateView.as_view(),
        name="pin_update",
    ),
    path(
        "@<str:username>/pin/<int:pk>/delete/",
        PinDeleteView.as_view(),
        name="pin_delete",
    ),
    path(
        "@<str:username>/pin/copy/<int:pk>/", PinCreateView.as_view(), name="pin_copy"
    ),
    # post
    path("@<str:username>/posts/", PostListView.as_view(), name="post_list"),
    path("@<str:username>/posts/rss/", UserPostFeed(), name="user_post_feed"),
    path(
        "@<str:username>/posts/<slug:project>/",
        PostListView.as_view(),
        name="post_list_project",
    ),
    path(
        "@<str:username>/posts/<slug:slug>/update",
        ProjectUpdateView.as_view(),
        name="project_update",
    ),
    path(
        "@<str:username>/posts/<str:project>/rss/",
        UserPostProjectFeed(),
        name="user_post_project_feed",
    ),
    path(
        "project-autocomplete/",
        ProjectAutocomplete.as_view(),
        name="project-autocomplete",
    ),
    path("@<str:username>/post/create/", PostCreateView.as_view(), name="post_create"),
    path(
        "@<str:username>/post/<int:pk>/",
        PostDetailView.as_view(),
        name="post_detail",
    ),
    path(
        "@<str:username>/post/<slug:slug>/",
        PostDetailView.as_view(),
        name="post_detail_slug",
    ),
    path(
        "@<str:username>/post/<int:pk>/update/",
        PostUpdateView.as_view(),
        name="post_update",
    ),
    path(
        "@<str:username>/post/<slug:slug>/update/",
        PostUpdateView.as_view(),
        name="post_update_slug",
    ),
    path(
        "@<str:username>/post/<int:pk>/delete/",
        PostDeleteView.as_view(),
        name="post_delete",
    ),
    path(
        "@<str:username>/post/<slug:slug>/delete/",
        PostDeleteView.as_view(),
        name="post_delete_slug",
    ),
    # say
    path("@<str:username>/says/", SayListView.as_view(), name="say_list"),
    path("@<str:username>/says/rss/", UserSayFeed(), name="user_say_feed"),
    path("@<str:username>/say/create/", SayCreateView.as_view(), name="say_create"),
    path("@<str:username>/say/<int:pk>/", SayDetailView.as_view(), name="say_detail"),
    path(
        "@<str:username>/say/<int:pk>/update/",
        SayUpdateView.as_view(),
        name="say_update",
    ),
    path(
        "@<str:username>/say/<int:pk>/delete/",
        SayDeleteView.as_view(),
        name="say_delete",
    ),
    # comment
    path(
        "@<str:username>/reply/<str:app_label>/<str:model_name>/<int:object_id>/",
        CommentCreateView.as_view(),
        name="comment_create",
    ),
    path(
        "@<str:username>/reply/<int:pk>/update/",
        CommentUpdateView.as_view(),
        name="comment_update",
    ),
    path(
        "@<str:username>/reply/<int:pk>/delete/",
        CommentDeleteView.as_view(),
        name="comment_delete",
    ),
    path(
        "@<str:username>/replied/",
        CommentListView.as_view(),
        name="replied",
    ),
    # repost
    path(
        "@<str:username>/repost/new/<int:activity_id>/",
        RepostCreateView.as_view(),
        name="repost_create",
    ),
    path(
        "@<str:username>/repost/<int:pk>/",
        RepostDetailView.as_view(),
        name="repost_detail",
    ),
    path(
        "@<str:username>/repost/<int:pk>/delete/",
        RepostDeleteView.as_view(),
        name="repost_delete",
    ),
    path(
        "@<str:username>/repost/<int:pk>/update/",
        RepostUpdateView.as_view(),
        name="repost_update",
    ),
    # tag
    path("tag/<str:tag>/", TagListView.as_view(), name="tag_list"),
    path(
        "@<str:username>/tag/<str:tag>/",
        TagUserListView.as_view(),
        name="tag_user_list",
    ),
    path("tag/<str:tag>/rss/", TagListFeed(), name="tag_list_feed"),
    path(
        "@<str:username>/tag/<str:tag>/rss",
        TagUserListFeed(),
        name="tag_user_list_feed",
    ),
    # luvlist
    path(
        "@<str:username>/list/create/",
        LuvListCreateView.as_view(),
        name="luvlist_create",
    ),
    path(
        "@<str:username>/list/<int:pk>/",
        LuvListDetailView.as_view(),
        name="luvlist_detail",
    ),
    path(
        "@<str:username>/list/<int:pk>/update/",
        LuvListUpdateView.as_view(),
        name="luvlist_update",
    ),
    path(
        "@<str:username>/list/<int:pk>/delete/",
        LuvListDeleteView.as_view(),
        name="luvlist_delete",
    ),
    path("@<str:username>/lists/", LuvListUserListView.as_view(), name="luvlist_list"),
    path(
        "@<str:username>/list/<int:pk>/surprise/",
        RandomizerDetailView.as_view(),
        name="surprise",
    ),
    path(
        "list/<int:pk>/",
        LuvListDetailView.as_view(),
        name="luvlist_detail_collab",
    ),
    path(
        "list/<int:pk>/update/",
        LuvListUpdateView.as_view(),
        name="luvlist_update_collab",
    ),
    path(
        "list/<int:pk>/surprise/",
        RandomizerDetailView.as_view(),
        name="surprise_collab",
    ),
    # move check-ins from individual apps/urls.py to write/urls.py
    ## Read
    path(
        "@<str:username>/read/checkin/<int:pk>/",
        ReadCheckInDetailView.as_view(),
        name="read_checkin_detail",
    ),
    path(
        "@<str:username>/read/checkin/<int:pk>/update/",
        ReadCheckInUpdateView.as_view(),
        name="read_checkin_update",
    ),
    path(
        "@<str:username>/read/checkin/<int:pk>/delete/",
        ReadCheckInDeleteView.as_view(),
        name="read_checkin_delete",
    ),
    path(
        "@<str:username>/read/checkins/",
        view=GenericReadCheckInUserListView.as_view(),
        name="read_checkin_user_list",
    ),
    ## Listen
    path(
        "@<str:username>/listen/checkin/<int:pk>/",
        ListenCheckInDetailView.as_view(),
        name="listen_checkin_detail",
    ),
    path(
        "@<str:username>/listen/checkin/<int:pk>/update/",
        ListenCheckInUpdateView.as_view(),
        name="listen_checkin_update",
    ),
    path(
        "@<str:username>/listen/checkin/<int:pk>/delete/",
        ListenCheckInDeleteView.as_view(),
        name="listen_checkin_delete",
    ),
    path(
        "@<str:username>/listen/checkins/",
        GenericListenCheckInUserListView.as_view(),
        name="listen_checkin_user_list",
    ),
    # Watch
    path(
        "@<str:username>/watch/checkin/<int:pk>/",
        WatchCheckInDetailView.as_view(),
        name="watch_checkin_detail",
    ),
    path(
        "@<str:username>/watch/checkin/<int:pk>/update/",
        WatchCheckInUpdateView.as_view(),
        name="watch_checkin_update",
    ),
    path(
        "@<str:username>/watch/checkin/<int:pk>/delete/",
        WatchCheckInDeleteView.as_view(),
        name="watch_checkin_delete",
    ),
    path(
        "@<str:username>/watch/checkins/",
        GenericWatchCheckInUserListView.as_view(),
        name="watch_checkin_user_list",
    ),
    # Play
    path(
        "@<str:username>/play/checkin/<int:pk>/",
        PlayCheckInDetailView.as_view(),
        name="play_checkin_detail",
    ),
    path(
        "@<str:username>/play/checkin/<int:pk>/update/",
        PlayCheckInUpdateView.as_view(),
        name="play_checkin_update",
    ),
    path(
        "@<str:username>/play/checkin/<int:pk>/delete/",
        PlayCheckInDeleteView.as_view(),
        name="play_checkin_delete",
    ),
    path(
        "@<str:username>/play/checkins/",
        PlayCheckInUserListView.as_view(),
        name="play_checkin_user_list",
    ),
]
