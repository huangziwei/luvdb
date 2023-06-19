from django.conf import settings
from django.db import models

from entity.models import Person, Role


# Create your models here.
class Track(models.Model):
    """
    A Work entity
    """

    # track meta data
    title = models.CharField(max_length=255)
    persons = models.ManyToManyField(Person, through="TrackRole", related_name="tracks")
    relase_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    language = models.CharField(max_length=255, blank=True, null=True)

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="tracks_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="tracks_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title


class TrackRole(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.track} - {self.name or self.person.name} - {self.role}"


# Release
class Release(models.Model):
    """
    An Release Entity
    """

    title = models.CharField(max_length=255)
    persons = models.ManyToManyField(
        Person, through="ReleaseRole", related_name="releases"
    )
    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    release_type = models.CharField(
        max_length=255, blank=True, null=True
    )  # album, single, etc.
    release_format = models.CharField(
        max_length=255, blank=True, null=True
    )  # CD, digital, etc.
    release_region = models.CharField(
        max_length=255, blank=True, null=True
    )  # Japan, USA, etc.
    isrc = models.CharField(
        max_length=255, blank=True, null=True
    )  # International Standard Recording Code

    # Entry metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="releases_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="releases_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title


class ReleaseRole(models.Model):
    """
    A Role a Person has in a Release
    """

    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    release = models.ForeignKey(Release, on_delete=models.CASCADE)
    role = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.role} in {self.release.title} by {self.person.name}"
