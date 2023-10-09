from django.urls import path

from .views import DiscoverListAllView, DiscoverPinListView, DiscoverPostListView, vote

app_name = "discover"
urlpatterns = [
    path("all", DiscoverListAllView.as_view(), name="all"),
    path("posts", DiscoverPostListView.as_view(), name="posts"),
    path("pins", DiscoverPinListView.as_view(), name="pins"),
    path(
        "vote/<str:content_type>/<int:object_id>/<str:vote_type>/",
        vote,
        name="vote",
    ),
]
