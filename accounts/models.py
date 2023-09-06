import pytz
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
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

    def __str__(self):
        return self.code


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
    is_public = models.BooleanField(default=False)
    timezone = models.CharField(
        max_length=50, choices=[(tz, tz) for tz in pytz.all_timezones], default="UTC"
    )

    RESERVED_USERNAMES = [
        "admin",
        "root",
        "system",
        "support",
        "about",
        "user",
        "read",
        "watch",
        "listen",
        "play",
        "write",
        "say",
        "pin",
        "post",
        "repost",
        "checkin",
        "release",
        "work",
        "instance",
        "game",
        "movie",
        "series",
        "episode",
        "issue",
        "book",
        "periodical",
    ]

    def save(self, *args, **kwargs):
        if self.username in self.RESERVED_USERNAMES:
            raise ValidationError("This username is reserved and cannot be registered.")

        # Check if the user has used an invitation code and hasn't been assigned an inviter yet
        if self.code_used:
            # # Save the user instance before creating the Follow and Activity instances
            super().save(*args, **kwargs)

            # Get or create a Follow instance for the new user following the inviter
            follow_new_user, created = Follow.objects.get_or_create(
                follower=self, followed=self.invited_by
            )

            # Get or create a Follow instance for the inviter following the new user
            follow_inviter, created = Follow.objects.get_or_create(
                follower=self.invited_by, followed=self
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


class InvitationRequest(models.Model):
    email = models.EmailField(unique=True)
    about_me = models.TextField(null=True, blank=True)
    is_invited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
