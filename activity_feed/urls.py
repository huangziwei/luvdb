from django.urls import path

from .views import ActivityFeedView, follow, unfollow

app_name = "activity_feed"
urlpatterns = [
    path("", ActivityFeedView.as_view(), name="activity_feed"),
    path("follow/<int:user_id>/", follow, name="follow"),
    path("unfollow/<int:user_id>/", unfollow, name="unfollow"),
]
