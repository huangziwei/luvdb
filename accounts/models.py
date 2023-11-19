import base64
import os
import secrets

import pytz
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.http import JsonResponse
from django.urls import reverse
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
    pure_text_mode = models.BooleanField(default=False)
    enable_federation = models.BooleanField(default=False)
    public_key = models.TextField(blank=True, null=True, editable=False)
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

    def get_absolute_url(self):
        return reverse("accounts:detail", kwargs={"username": self.username})

    def save(self, *args, **kwargs):
        if self.username in self.RESERVED_USERNAMES:
            raise ValidationError("This username is reserved and cannot be registered.")

        # Check if the user has used an invitation code
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

        if self.enable_federation:
            # Check if the user already has a public key
            if not self.public_key:
                private_key, public_key = self.generate_key_pair()
                encoded_private_key = base64.b64encode(private_key).decode("utf-8")

                # Store the encoded private key in the environment file
                with open(settings.PRIVATEKEY_PATH, "a") as file:
                    file.write(f"{self.username}={encoded_private_key}\n")

                # Store public key in the database
                self.public_key = public_key.decode("utf-8")

    def generate_key_pair(self):
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        # Serialize private key
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),  # Can be replaced with actual encryption
        )

        # Generate public key
        public_key = private_key.public_key()
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return private_key_bytes, public_key_bytes


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


@login_required
def get_followed_usernames(request):
    usernames = list(
        Follow.objects.filter(follower=request.user).values_list(
            "followed__username", flat=True
        )
    )
    return JsonResponse({"usernames": usernames})


class AppPassword(models.Model):
    user = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="app_passwords"
    )
    name = models.CharField(max_length=100)
    token = models.CharField(max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(20)  # Generates a secure token
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.user.username}"


def encrypt_password(raw_password):
    cipher_suite = Fernet(settings.FERNET_KEY)
    return cipher_suite.encrypt(raw_password.encode()).decode()


def decrypt_password(encrypted_password):
    cipher_suite = Fernet(settings.FERNET_KEY)
    return cipher_suite.decrypt(encrypted_password.encode()).decode()


class BlueSkyAccount(models.Model):
    """Model for storing user's BlueSky account details."""

    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="bluesky_account"
    )
    bluesky_handle = models.CharField(max_length=100, unique=True)
    bluesky_pds_url = models.URLField(max_length=255)
    _bluesky_app_password = models.CharField(max_length=128)

    def set_bluesky_app_password(self, raw_password):
        self._bluesky_app_password = encrypt_password(raw_password)

    def get_bluesky_app_password(self):
        return decrypt_password(self._bluesky_app_password)

    def __str__(self):
        return self.bluesky_handle


class MastodonAccount(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="mastodon_account"
    )
    mastodon_handle = models.CharField(max_length=100, unique=True)
    _mastodon_access_token = models.CharField(max_length=255)

    # Method to set the encrypted access token
    def set_mastodon_access_token(self, raw_token):
        self._mastodon_access_token = encrypt_password(
            raw_token
        )  # Assuming you have an encryption method

    # Method to get the decrypted access token
    def get_mastodon_access_token(self):
        return decrypt_password(
            self._mastodon_access_token
        )  # Assuming you have a decryption method

    def __str__(self):
        return self.mastodon_handle


class FediverseFollower(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    follower_uri = models.URLField(unique=True)
    follower_inbox = models.URLField(blank=True, null=True)
    follower_shared_inbox = models.URLField(blank=True, null=True)
    preferred_headers = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.follower_uri
