import re

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DeleteView, ListView

from .models import Notification


class NotificationListView(ListView):
    model = Notification
    template_name = "notify/notification_list.html"
    paginate_by = 50

    def get_queryset(self):
        return self.request.user.notifications.order_by("-timestamp")


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


def find_mentions(text):
    pattern = re.compile(r"@(\w+)")
    return pattern.findall(text)


def create_mentions_notifications(user, text, content_object):
    mentions = find_mentions(text)
    for username in mentions:
        try:
            mentioned_user = get_user_model().objects.get(username=username)
            if mentioned_user != user:
                author_url = reverse("accounts:detail", args=[user.username])
                content_url = content_object.get_absolute_url()
                content_name = content_object.__class__.__name__.capitalize()
                message = f'<a href="{author_url}">@{user.username}</a> mentioned you in a <a href="{content_url}">{content_name}</a>.'

                Notification.objects.create(
                    recipient=mentioned_user,
                    sender_content_type=ContentType.objects.get_for_model(user),
                    sender_object_id=user.id,
                    notification_type="mention",
                    message=message,
                )
        except get_user_model().DoesNotExist:
            pass
