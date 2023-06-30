import os
import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from entity.models import Entity, Person, Role


# helpers
def rename_release_cover(instance, filename):
    _, extension = os.path.splitext(filename)
    unique_id = uuid.uuid4()
    directory_name = (
        f"{slugify(instance.title, allow_unicode=True)}-{instance.release_date}"
    )
    new_name = f"{unique_id}{extension}"
    return os.path.join("covers", directory_name, new_name)


class Label(Entity):
    """
    A Publisher entity
    """

    # publisher meta data
    history = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    founded_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    closed_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD

    def __str__(self):
        if self.location:
            return f"{self.location}: {self.name}"
        return self.name


class Work(models.Model):
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=100, blank=True, null=True)  # rock, pop, etc.
    persons = models.ManyToManyField(
        Person, through="WorkRole", related_name="listen_works"
    )
    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD

    def __str__(self):
        return self.title


class WorkRole(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="listen_workrole_set",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="listen_workrole_set",
    )

    def __str__(self):
        return f"{self.role} of {self.work} by {self.person}"


class Track(models.Model):
    """
    A Work entity
    """

    # track meta data
    title = models.CharField(max_length=255)
    romanized_title = models.CharField(max_length=255, blank=True, null=True)
    persons = models.ManyToManyField(Person, through="TrackRole", related_name="tracks")
    relase_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    length = models.CharField(max_length=10, blank=True, null=True)  # HH:MM:SS
    genre = models.CharField(max_length=255, blank=True, null=True)  # rock, pop, etc.

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
    alt_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.track} - {self.alt_name or self.person.name} - {self.role}"


# Release
class Release(models.Model):
    """
    An Release Entity
    """

    cover = models.ImageField(upload_to=rename_release_cover, null=True, blank=True)
    cover_sens = models.BooleanField(default=False, null=True, blank=True)

    # Release meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    persons = models.ManyToManyField(
        Person, through="ReleaseRole", related_name="releases"
    )
    tracks = models.ManyToManyField(
        Track, through="TrackInRelease", related_name="releases"
    )
    label = models.ManyToManyField(Label, related_name="releases")

    genre = models.CharField(max_length=255, blank=True, null=True)  # rock, pop, etc.
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


class TrackInRelease(models.Model):
    release = models.ForeignKey(Release, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    track_order = models.PositiveIntegerField()

    class Meta:
        ordering = ["track_order"]

    def __str__(self):
        return f"{self.release.title}, {self.track.title}"
