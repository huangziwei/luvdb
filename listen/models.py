import os
import uuid
from io import BytesIO

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from PIL import Image

from activity_feed.models import Activity
from entity.models import Entity, Person, Role
from write.models import create_mentions_notifications, handle_tags


# helpers
def rename_release_cover(instance, filename):
    if filename is None:
        filename = "default.jpg"
    _, extension = os.path.splitext(filename)
    unique_id = uuid.uuid4()

    base_name = slugify(instance.title, allow_unicode=True)

    # Check if the instance has a release_date attribute and if it's not None
    if hasattr(instance, "release_date") and instance.release_date:
        directory_name = f"{base_name}-{instance.release_date}"
    else:
        directory_name = base_name

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
    wikipedia = models.URLField(blank=True, null=True)
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


class Genre(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Work(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True, null=True)
    romanized_title = models.CharField(max_length=200, blank=True, null=True)
    persons = models.ManyToManyField(
        Person, through="WorkRole", related_name="listen_works"
    )
    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    genres = models.ManyToManyField(Genre, related_name="listen_works", blank=True)
    wikipedia = models.URLField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:work_detail", kwargs={"pk": self.pk})


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
    alt_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.role} of {self.work} by {self.person}"


class Track(models.Model):
    """
    A Work entity
    """

    # track meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    romanized_title = models.CharField(max_length=255, blank=True, null=True)
    persons = models.ManyToManyField(Person, through="TrackRole", related_name="tracks")
    work = models.ForeignKey(
        Work, on_delete=models.SET_NULL, null=True, blank=True, related_name="tracks"
    )
    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    genres = models.ManyToManyField(Genre, related_name="tracks", blank=True)

    length = models.CharField(max_length=10, blank=True, null=True)  # HH:MM:SS
    note = models.TextField(blank=True, null=True)

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

    def get_absolute_url(self):
        return reverse("listen:track_detail", kwargs={"pk": self.pk})


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
    romanized_title = models.CharField(max_length=255, blank=True, null=True)
    persons = models.ManyToManyField(
        Person, through="ReleaseRole", related_name="releases"
    )
    tracks = models.ManyToManyField(
        Track, through="ReleaseTrack", related_name="releases"
    )
    label = models.ManyToManyField(Label, related_name="releases")
    genres = models.ManyToManyField(Genre, related_name="releases", blank=True)
    wikipedia = models.URLField(blank=True, null=True)

    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    RELEASE_TYPES = [
        ("LP", "LP"),
        ("EP", "EP"),
        ("Single", "Single"),
    ]
    release_type = models.CharField(
        max_length=255, choices=RELEASE_TYPES, blank=True, null=True
    )

    RECORDING_TYPES = [
        ("Studio", "Studio"),
        ("Live", "Live"),
        ("Studio and Live", "Studio and Live"),
        ("Compilation", "Compilation"),
        ("Box Set", "Box Set"),
        ("Bootleg", "Bootleg"),
    ]
    recording_type = models.CharField(
        max_length=255, choices=RECORDING_TYPES, blank=True, null=True
    )
    release_format = models.CharField(
        max_length=255, blank=True, null=True
    )  # CD, digital, etc.
    release_region = models.CharField(
        max_length=255, blank=True, null=True
    )  # Japan, USA, etc.
    release_length = models.CharField(max_length=10, blank=True, null=True)  # HH:MM:SS
    isrc = models.CharField(
        max_length=255, blank=True, null=True
    )  # International Standard Recording Code
    spotify_url = models.URLField(blank=True, null=True)
    apple_music_url = models.URLField(blank=True, null=True)
    kkbox_url = models.URLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)

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
    listencheckin = GenericRelation("ListenCheckIn")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:release_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Release.objects.get(pk=self.pk)
            # If the cover has been updated
            if old_instance.cover != self.cover:
                # Delete the old cover
                old_instance.cover.delete(save=False)

        super().save(*args, **kwargs)

        if self.cover:
            img = Image.open(self.cover.open(mode="rb"))

            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)

                # Save the image to a BytesIO object
                temp_file = BytesIO()
                img.save(temp_file, format=img.format)
                temp_file.seek(0)

                # remove the original image
                self.cover.delete(save=False)

                # Save the BytesIO object to the FileField
                self.cover.save(
                    self.cover.name, ContentFile(temp_file.read()), save=False
                )

            img.close()

        super().save(*args, **kwargs)

    def model_name(self):
        return "Release"


class ReleaseRole(models.Model):
    release = models.ForeignKey(Release, on_delete=models.CASCADE)
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_query_name="release_roles",
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    alt_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.release} - {self.alt_name or self.person.name} - {self.role}"


class ReleaseTrack(models.Model):
    release = models.ForeignKey(Release, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, null=True, blank=True)
    alt_title = models.CharField(max_length=255, blank=True, null=True)
    disk = models.CharField(max_length=10, default="1")
    order = models.PositiveIntegerField(default=1, null=True, blank=True)

    class Meta:
        ordering = ["disk", "order"]

    def __str__(self):
        return f"{self.release.title}, {self.track.title}"


class ListenCheckIn(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    STATUS_CHOICES = [
        ("to_listen", "To Listen"),
        ("looping", "Looping"),
        ("listened", "Listened"),
        ("listening", "Listening"),
        ("paused", "Paused"),
        ("abandoned", "Abandoned"),
        ("subscribed", "Subscribed"),
        ("unsubscribed", "Unsubscribed"),
        ("sampled", "Sampled"),
    ]
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
    share_to_feed = models.BooleanField(default=False)
    content = models.TextField(
        null=True, blank=True
    )  # Any thoughts or comments at this check-in.
    timestamp = models.DateTimeField(auto_now_add=True)
    progress = models.CharField(max_length=20, null=True, blank=True)
    TOTAL_LISTEN_TIME = "TT"
    LOOP_TIME = "LT"
    PROGRESS_TYPE_CHOICES = [
        (TOTAL_LISTEN_TIME, "Accumulated Listen Time"),
        (LOOP_TIME, "Loop Time"),
    ]
    progress_type = models.CharField(
        max_length=2,
        choices=PROGRESS_TYPE_CHOICES,
        default=LOOP_TIME,
    )
    comments = GenericRelation("write.Comment")
    comments_enabled = models.BooleanField(default=True)
    tags = models.ManyToManyField("write.Tag", blank=True)
    reposts = GenericRelation("write.Repost")

    def get_absolute_url(self):
        return reverse("listen:listen_checkin_detail", args=[str(self.id)])

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="listencheckin", object_id=self.id
            )
            return activity.id
        except ObjectDoesNotExist:
            return None

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.share_to_feed:
            # Only create activity if share_on_feed is True
            Activity.objects.create(
                user=self.user,
                activity_type="listen-check-in",
                content_object=self,
            )
        else:
            print("Not creating activity")
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


class Podcast(models.Model):
    """
    A Podcast Entity
    """

    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    cover = models.ImageField(upload_to=rename_release_cover, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    publisher = models.CharField(
        max_length=255, blank=True, null=True
    )  # Can be linked to the existing `Label` entity if desired
    genres = models.ManyToManyField(Genre, related_name="podcasts", blank=True)
    rss_feed_url = models.URLField(unique=True)  # To fetch episodes
    website_url = models.URLField(blank=True, null=True)  # Original podcast page
    episodes = models.JSONField(blank=True, null=True)
    language = models.CharField(max_length=20, blank=True, null=True)
    copyright = models.CharField(max_length=255, blank=True, null=True)
    last_updated = models.DateTimeField(blank=True, null=True)
    categories = models.JSONField(blank=True, null=True)
    explicit = models.BooleanField(null=True, blank=True, default=False)
    author = models.CharField(max_length=255, blank=True, null=True)

    listencheckin = GenericRelation("ListenCheckIn")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:podcast_detail", kwargs={"pk": self.pk})

    def model_name(self):
        return "Podcast"
