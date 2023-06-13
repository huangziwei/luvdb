from django.urls import path

from .views import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationListView,
)

app_name = "notify"
urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification_list"),
    path(
        "notifications/<int:pk>/read/",
        MarkNotificationReadView.as_view(),
        name="mark_as_read",
    ),
    path(
        "notifications/read_all/",
        MarkAllNotificationsReadView.as_view(),
        name="mark_all_as_read",
    ),
]
