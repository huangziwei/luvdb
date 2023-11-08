import re

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DeleteView, ListView

from .models import MutedNotification, Notification


class NotificationListView(ListView):
    model = Notification
    template_name = "notify/notification_list.html"
    paginate_by = 50

    def get_queryset(self):
        notifications = self.request.user.notifications.order_by("-timestamp").all()

        # Convert queryset to list to work with individual instances
        notifications = list(notifications)

        muted_notifications = set(
            MutedNotification.objects.filter(user=self.request.user).values_list(
                "content_type", "object_id"
            )
        )

        for notification in notifications:
            key = (
                notification.subject_content_type_id,
                notification.subject_object_id,
            )  # Adjust this line
            notification.is_muted = key in muted_notifications

        return notifications


class MarkNotificationReadView(View):
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(Notification, pk=kwargs["pk"])
        notification.read = True
        notification.save()
        return redirect("notify:notification_list")


class MarkAllNotificationsReadView(View):
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(recipient=request.user, read=False).update(
            read=True
        )
        return redirect("notify:notification_list")


class NotificationDeleteView(DeleteView):
    model = Notification
    success_url = reverse_lazy("notify:notification_list")

    def get_queryset(self):
        return self.request.user.notifications.all()


class NotificationDeleteAllView(View):
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(recipient=request.user).delete()
        return redirect("notify:notification_list")


class MuteNotificationView(View):
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(Notification, pk=kwargs["pk"])

        content_type = notification.subject_content_type
        object_id = notification.subject_object_id

        muted_notification, created = MutedNotification.objects.get_or_create(
            user=request.user, content_type=content_type, object_id=object_id
        )

        if not created:
            muted_notification.delete()

        return redirect("notify:notification_list")


def find_mentions(text):
    pattern = re.compile(r"@(\w+)")
    return pattern.findall(text)


def create_mentions_notifications(user, text, content_object):
    mentions = find_mentions(text)
    for username in mentions:
        try:
            mentioned_user = get_user_model().objects.get(username=username)
            if mentioned_user != user:
                user_url = reverse("accounts:detail", args=[user.username])
                user_name = user.display_name if user.display_name else user.username
                content_url = content_object.get_absolute_url()
                content_name = content_object.__class__.__name__.capitalize()
                if "checkin" in content_name:
                    content_name = f"{content_name[:-7]} Check-in"
                message = f'<a href="{user_url}">@{user.username}</a> mentioned you in a <a href="{content_url}">{content_name}</a>.'

                notification = Notification.objects.create(
                    recipient=mentioned_user,
                    sender_content_type=ContentType.objects.get_for_model(user),
                    sender_object_id=user.id,
                    subject_content_type=ContentType.objects.get_for_model(
                        content_object
                    ),
                    subject_object_id=content_object.id,
                    notification_type="mention",
                    message=message,
                )
                notification.save()
                content_url_with_read_marker = (
                    f"{content_url}?mark_read={notification.id}"
                )
                # Update the message with the new URL containing the marker
                notification.message = f'<a href="{user_url}">@{user_name}</a> mentioned in a <a href="{content_url_with_read_marker}">{content_name}</a>.'
                notification.save()

        except get_user_model().DoesNotExist:
            pass
