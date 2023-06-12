from django.urls import path

from .views import ActivityFeedDeleteView, ActivityFeedView, follow, unfollow

app_name = "activity_feed"
urlpatterns = [
    path("", ActivityFeedView.as_view(), name="activity_feed"),
    path(
        "activity/<int:pk>/delete/",
        ActivityFeedDeleteView.as_view(),
        name="activity_delete",
    ),
    path("follow/<int:user_id>/", follow, name="follow"),
    path("unfollow/<int:user_id>/", unfollow, name="unfollow"),
]
