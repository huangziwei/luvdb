from django.urls import path

from .views import (
    PinCreateView,
    PinDetailView,
    PinListView,
    PinUpdateView,
    PostCreateView,
    PostDetailView,
    PostListView,
    PostUpdateView,
    SayCreateView,
    SayDetailView,
    SayListView,
    SayUpdateView,
    add_comment,
)

app_name = "write"
urlpatterns = [
    path("pins/<str:username>", PinListView.as_view(), name="pin_list"),
    path("pin/new/", PinCreateView.as_view(), name="pin_create"),
    path("pin/<int:pk>/", PinDetailView.as_view(), name="pin_detail"),
    path("pin/<int:pk>/update/", PinUpdateView.as_view(), name="pin_update"),
    path("posts/<str:username>", PostListView.as_view(), name="post_list"),
    path("post/new/", PostCreateView.as_view(), name="post_create"),
    path("post/<int:pk>/", PostDetailView.as_view(), name="post_detail"),
    path("post/<int:pk>/update/", PostUpdateView.as_view(), name="post_update"),
    path("says/<str:username>/", SayListView.as_view(), name="say_list"),
    path("say/new/", SayCreateView.as_view(), name="say_create"),
    path("say/<int:pk>/", SayDetailView.as_view(), name="say_detail"),
    path("say/<int:pk>/update/", SayUpdateView.as_view(), name="say_update"),
    path(
        "add_comment/<str:app_label>/<str:model_name>/<int:object_id>/",
        add_comment,
        name="add_comment",
    ),
]
