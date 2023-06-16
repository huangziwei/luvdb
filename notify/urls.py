from django.urls import path

from .views import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationDeleteAllView,
    NotificationDeleteView,
    NotificationListView,
)

app_name = "notify"
urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification_list"),
    path("delete/<int:pk>/", NotificationDeleteView.as_view(), name="delete"),
    path("delete_all/", NotificationDeleteAllView.as_view(), name="delete_all"),
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
