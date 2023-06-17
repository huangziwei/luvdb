from django.urls import path, re_path

from .views import (
    CommentCreateView,
    CommentDeleteView,
    CommentUpdateView,
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
)

app_name = "write"
urlpatterns = [
    # pin
    path("pins/<str:username>", PinListView.as_view(), name="pin_list"),
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
    path("posts/<str:username>", PostListView.as_view(), name="post_list"),
    path("post/create/", PostCreateView.as_view(), name="post_create"),
    path("post/<int:pk>/", PostDetailView.as_view(), name="post_detail"),
    path("post/<int:pk>/update/", PostUpdateView.as_view(), name="post_update"),
    path("post/<int:pk>/delete/", PostDeleteView.as_view(), name="post_delete"),
    # say
    path("says/<str:username>/", SayListView.as_view(), name="say_list"),
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
    path("tag/<str:tag>/", TagListView.as_view(), name="tag_list"),
    path(
        "repost/new/<int:activity_id>/",
        RepostCreateView.as_view(),
        name="repost_create",
    ),
    path("repost/<int:pk>/", RepostDetailView.as_view(), name="repost_detail"),
    path("repost/<int:pk>/delete/", RepostDeleteView.as_view(), name="repost_delete"),
    path("repost/<int:pk>/update/", RepostUpdateView.as_view(), name="repost_update"),
]
