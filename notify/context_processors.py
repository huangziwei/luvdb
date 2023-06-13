from .models import Notification


def notifications(request):
    if request.user.is_authenticated:
        new_notifications = Notification.objects.filter(
            recipient=request.user, read=False
        ).count()
        recent_notifications = Notification.objects.filter(
            recipient=request.user
        ).order_by("-timestamp")[:5]
        return {
            "new_notifications": new_notifications,
            "recent_notifications": recent_notifications,
        }
    else:
        return {}
