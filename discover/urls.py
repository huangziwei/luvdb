from django.urls import path

from .views import (
    DiscoverListAllView,
    DiscoverLuvListListView,
    DiscoverPinListView,
    DiscoverPostListView,
    vote,
)

app_name = "discover"
urlpatterns = [
    path("all", DiscoverListAllView.as_view(), name="all"),
    path("lists", DiscoverLuvListListView.as_view(), name="lists"),
    path("posts", DiscoverPostListView.as_view(), name="posts"),
    path("pins", DiscoverPinListView.as_view(), name="pins"),
    path(
        "vote/<str:content_type>/<int:object_id>/<str:vote_type>/",
        vote,
        name="vote",
    ),
]
