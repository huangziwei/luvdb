from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("comment", "Comment"),
        ("mention", "Mention"),
        ("repost", "Repost"),
        ("follow", "Follow"),
        ("delete", "Delete"),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="notifications", on_delete=models.CASCADE
    )
    sender_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True
    )
    sender_object_id = models.PositiveIntegerField(null=True)
    sender_object = GenericForeignKey("sender_content_type", "sender_object_id")

    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.recipient.username} at {self.timestamp}"

    def is_delete(self):
        return (
            self.notification_type == "comment_on_deleted"
            or self.notification_type == "comment_deleted_by_author"
        )
