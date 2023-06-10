import random
import string

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.crypto import get_random_string


class InvitationCode(models.Model):
    """Model representing invitation codes."""

    code = models.CharField(max_length=100, unique=True, default=get_random_string(8))
    is_used = models.BooleanField(default=False)


class CustomUser(AbstractUser):
    """Custom user model."""

    code_used = models.OneToOneField(
        InvitationCode, null=True, blank=True, on_delete=models.SET_NULL
    )

    display_name = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
