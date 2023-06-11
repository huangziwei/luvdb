from django.urls import path

from .views import (
    PostCreateView,
    PostDetailView,
    PostListView,
    SayCreateView,
    SayDetailView,
    SayListView,
)

app_name = "write"
urlpatterns = [
    path("posts/<str:username>", PostListView.as_view(), name="post_list"),
    path("post/new/", PostCreateView.as_view(), name="post_create"),
    path("post/<int:pk>/", PostDetailView.as_view(), name="post_detail"),
    path("says/<str:username>/", SayListView.as_view(), name="say_list"),
    path("say/new/", SayCreateView.as_view(), name="say_create"),
    path("say/<int:pk>/", SayDetailView.as_view(), name="say_detail"),
]
