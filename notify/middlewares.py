from django.shortcuts import get_object_or_404
from django.utils.deprecation import MiddlewareMixin

from .models import Notification


class MarkNotificationReadMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if "mark_read" in request.GET:
            notification_id = request.GET.get("mark_read")
            if notification_id:
                notification = get_object_or_404(Notification, pk=notification_id)
                # Only mark as read if the request user is the recipient
                if notification.recipient_id == request.user.id:
                    notification.read = True
                    notification.save()
