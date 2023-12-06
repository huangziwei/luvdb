import auto_prefetch
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

User = get_user_model()


class Vote(auto_prefetch.Model):
    UPVOTE = 1
    DOWNVOTE = -1
    VOTE_CHOICES = [
        (UPVOTE, "Upvote"),
        (DOWNVOTE, "Downvote"),
    ]

    user = auto_prefetch.ForeignKey(User, on_delete=models.CASCADE)
    content_type = auto_prefetch.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    value = models.SmallIntegerField(choices=VOTE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
