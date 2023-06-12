import random
import string

from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.crypto import get_random_string

from activity_feed.models import Activity, Follow


class InvitationCode(models.Model):
    """Model representing invitation codes."""

    code = models.CharField(max_length=100, unique=True, blank=True)
    is_used = models.BooleanField(default=False)
    generated_by = models.ForeignKey(
        "CustomUser",
        related_name="codes_generated",
        on_delete=models.CASCADE,
        null=True,
    )
    generated_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.code:
            # Generate a new code if one hasn't been assigned yet
            self.code = get_random_string(8)
        super().save(*args, **kwargs)


class CustomUser(AbstractUser):
    """Custom user model."""

    code_used = models.OneToOneField(
        InvitationCode,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="used_by",
    )
    invited_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True
    )
    display_name = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Check if the user has used an invitation code and hasn't been assigned an inviter yet
        if self.code_used:
            # Save the user instance before creating the Follow and Activity instances
            super().save(*args, **kwargs)

            # Create a Follow instance
            follow = Follow.objects.create(follower=self, followed=self.invited_by)

            # Create an Activity instance
            content_type = ContentType.objects.get_for_model(Follow)
            Activity.objects.create(
                user=self,
                activity_type="follow",
                content_type=content_type,
                object_id=follow.id,
            )
        else:
            super().save(*args, **kwargs)


@receiver(post_save, sender=Follow)
def create_follow_activity(sender, instance, created, **kwargs):
    if created:
        Activity.objects.create(
            user=instance.follower,
            activity_type="follow",
            content_object=instance,
        )
