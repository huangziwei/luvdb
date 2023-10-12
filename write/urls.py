from django.urls import path, re_path

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
    content_detail_redirect,
)

app_name = "write"
urlpatterns = [
    # pin
    path("u/<str:username>/pins/", PinListView.as_view(), name="pin_list"),
    path("u/<str:username>/pins/rss/", UserPinFeed(), name="user_pin_feed"),
    re_path(
        r"^pins/from/(?P<root_url>.+)/$",
        PinsFromURLView.as_view(),
        name="pins_from_url",
    ),
    path("pin/create/", PinCreateView.as_view(), name="pin_create"),
    path("pin/<int:pk>/", PinDetailView.as_view(), name="pin_detail"),
    path("pin/<int:pk>/update/", PinUpdateView.as_view(), name="pin_update"),
    path("pin/<int:pk>/delete/", PinDeleteView.as_view(), name="pin_delete"),
    path("pin/copy/<int:pk>/", PinCreateView.as_view(), name="pin_copy"),
    # post
    path("u/<str:username>/posts/", PostListView.as_view(), name="post_list"),
    path(
        "u/<str:username>/posts/<str:project>/",
        PostListView.as_view(),
        name="post_list_project",
    ),
    path(
        "project-autocomplete/",
        ProjectAutocomplete.as_view(),
        name="project-autocomplete",
    ),
    path("u/<str:username>/posts/rss/", UserPostFeed(), name="user_post_feed"),
    path(
        "u/<str:username>/posts/<str:project>/rss/",
        UserPostProjectFeed(),
        name="user_post_project_feed",
    ),
    path("post/create/", PostCreateView.as_view(), name="post_create"),
    path("post/<int:pk>/", PostDetailView.as_view(), name="post_detail"),
    path("post/<int:pk>/update/", PostUpdateView.as_view(), name="post_update"),
    path("post/<int:pk>/delete/", PostDeleteView.as_view(), name="post_delete"),
    # say
    path("u/<str:username>/says/", SayListView.as_view(), name="say_list"),
    path("u/<str:username>/says/rss/", UserSayFeed(), name="user_say_feed"),
    path("say/create/", SayCreateView.as_view(), name="say_create"),
    path("say/<int:pk>/", SayDetailView.as_view(), name="say_detail"),
    path("say/<int:pk>/update/", SayUpdateView.as_view(), name="say_update"),
    path("say/<int:pk>/delete/", SayDeleteView.as_view(), name="say_delete"),
    # comment
    path(
        "comment/<str:app_label>/<str:model_name>/<int:object_id>/",
        CommentCreateView.as_view(),
        name="comment_create",
    ),
    path(
        "comment/<int:pk>/update/", CommentUpdateView.as_view(), name="comment_update"
    ),
    path(
        "comment/<int:pk>/delete/", CommentDeleteView.as_view(), name="comment_delete"
    ),
    # repost
    path(
        "repost/new/<int:activity_id>/",
        RepostCreateView.as_view(),
        name="repost_create",
    ),
    path("repost/<int:pk>/", RepostDetailView.as_view(), name="repost_detail"),
    path("repost/<int:pk>/delete/", RepostDeleteView.as_view(), name="repost_delete"),
    path("repost/<int:pk>/update/", RepostUpdateView.as_view(), name="repost_update"),
    # tag
    path("tag/<str:tag>/", TagListView.as_view(), name="tag_list"),
    path(
        "u/<str:username>/tag/<str:tag>/",
        TagUserListView.as_view(),
        name="tag_user_list",
    ),
    path("tag/<str:tag>/rss/", TagListFeed(), name="tag_list_feed"),
    path(
        "u/<str:username>/tag/<str:tag>/rss",
        TagUserListFeed(),
        name="tag_user_list_feed",
    ),
    # luvlist
    path("luvlist/create/", LuvListCreateView.as_view(), name="luvlist_create"),
    path("luvlist/<int:pk>/", LuvListDetailView.as_view(), name="luvlist_detail"),
    path(
        "luvlist/<int:pk>/update/", LuvListUpdateView.as_view(), name="luvlist_update"
    ),
    path(
        "luvlist/<int:pk>/delete/", LuvListDeleteView.as_view(), name="luvlist_delete"
    ),
    path(
        "u/<str:username>/luvlists/", LuvListUserListView.as_view(), name="luvlist_list"
    ),
    path(
        "random_content/<int:content_id>/",
        content_detail_redirect,
        name="content_detail_redirect",
    ),
    path("luvlist/<int:pk>/random/", RandomizerDetailView.as_view(), name="randomizer"),
]
