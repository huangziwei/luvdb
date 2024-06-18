import base64
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

import auto_prefetch
import markdown
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.safestring import mark_safe


class Activity(auto_prefetch.Model):
    user = auto_prefetch.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=100, default="default_value")
    timestamp = models.DateTimeField(auto_now_add=True)

    # These fields are for the object that the activity is related to.
    # For example, if the activity is a post, the object_id would be the id of the post.
    content_type = auto_prefetch.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    comments = GenericRelation("write.Comment")
    reposts = GenericRelation("write.Repost")

    # visibility field
    VISIBILITY_PUBLIC = "PU"
    VISIBILITY_MENTIONED = "ME"
    VISIBILITY_FOLLOWERS = "FO"
    VISIBILITY_PRIVATE = "PR"

    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, "Public"),
        (VISIBILITY_MENTIONED, "Mentioned"),
        (VISIBILITY_FOLLOWERS, "Followers"),
        (VISIBILITY_PRIVATE, "Private"),
    ]

    visibility = models.CharField(
        max_length=2,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
    )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        was_update = False
        if not is_new:
            # Retrieve the current content_object (Say instance)
            current_content_object = self.content_object
            # Compare timestamps to check for updates
            was_update = (
                current_content_object.updated_at > current_content_object.timestamp
            )

        # Call the real save method
        super(Activity, self).save(*args, **kwargs)


class Follow(auto_prefetch.Model):
    follower = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="following",
        related_query_name="following",
        on_delete=models.CASCADE,
    )
    followed = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="followers", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta(auto_prefetch.Model.Meta):
        unique_together = ("follower", "followed")


class Block(auto_prefetch.Model):
    blocker = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="blocking",
        on_delete=models.CASCADE,
    )
    blocked = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="blocked_by",
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta(auto_prefetch.Model.Meta):
        unique_together = ("blocker", "blocked")
