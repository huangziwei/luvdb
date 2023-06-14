from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

from notify.models import Notification


class Activity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=100, default="default_value")
    timestamp = models.DateTimeField(auto_now_add=True)

    # These fields are for the object that the activity is related to.
    # For example, if the activity is a post, the object_id would be the id of the post.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    comments = GenericRelation("write.Comment")
    reposts = GenericRelation("write.Repost")


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="following",
        related_query_name="following",
        on_delete=models.CASCADE,
    )
    followed = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="followers", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "followed")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            follower_url = reverse("accounts:detail", args=[self.follower.username])
            follower_name = (
                self.follower.display_name
                if self.follower.display_name
                else self.follower.username
            )
            message = f'<a href="{follower_url}">@{follower_name}</a> followed you.'

            Notification.objects.create(
                recipient=self.followed,
                sender_content_type=ContentType.objects.get_for_model(self.follower),
                sender_object_id=self.follower.id,
                notification_type="follow",
                message=message,
            )
