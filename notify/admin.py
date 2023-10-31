from django.contrib import admin

from .models import MutedNotification, Notification


class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "notification_type", "message", "timestamp", "read")
    list_filter = ("notification_type", "read")
    search_fields = ("recipient__username", "message", "notification_type")


class MutedNotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "content_type", "object_id")
    list_filter = ("user", "content_type")
    search_fields = ("user__username", "content_type__name", "object_id")


admin.site.register(Notification, NotificationAdmin)
admin.site.register(MutedNotification, MutedNotificationAdmin)
