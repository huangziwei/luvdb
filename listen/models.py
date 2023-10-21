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
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image

from activity_feed.models import Activity
from entity.models import Company, Creator, Role
from read.models import Book, Instance, LanguageField, standardize_date
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
    other_titles = models.TextField(blank=True, null=True)
    romanized_title = models.CharField(max_length=200, blank=True, null=True)
    creators = models.ManyToManyField(
        Creator, through="WorkRole", related_name="listen_works"
    )
    release_date = models.CharField(max_length=10, blank=True, null=True)
    recorded_date = models.CharField(max_length=10, blank=True, null=True)
    genres = models.ManyToManyField(Genre, related_name="listen_works", blank=True)
    wikipedia = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:work_detail", kwargs={"pk": self.pk})


class WorkRole(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    creator = models.ForeignKey(
        Creator,
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
        return f"{self.role} of {self.work} by {self.creator}"


class Track(models.Model):
    """
    A Work entity
    """

    # track meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    other_titles = models.TextField(blank=True, null=True)
    romanized_title = models.CharField(max_length=255, blank=True, null=True)
    creators = models.ManyToManyField(
        Creator, through="TrackRole", related_name="tracks"
    )
    work = models.ForeignKey(
        Work, on_delete=models.SET_NULL, null=True, blank=True, related_name="tracks"
    )
    release_date = models.CharField(max_length=10, blank=True, null=True)
    recorded_date = models.CharField(max_length=10, blank=True, null=True)

    genres = models.ManyToManyField(Genre, related_name="tracks", blank=True)

    length = models.CharField(max_length=10, blank=True, null=True)  # HH:MM:SS
    isrc = models.CharField(
        max_length=255, blank=True, null=True
    )  # International Standard Recording Code
    wikipedia = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

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
    creator = models.ForeignKey(
        Creator, on_delete=models.CASCADE, null=True, blank=True
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    alt_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.track} - {self.alt_name or self.creator.name} - {self.role}"


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
    other_titles = models.TextField(blank=True, null=True)

    creators = models.ManyToManyField(
        Creator, through="ReleaseRole", related_name="releases"
    )
    tracks = models.ManyToManyField(
        Track, through="ReleaseTrack", related_name="releases"
    )

    label = models.ManyToManyField(Company, related_name="releases")
    genres = models.ManyToManyField(Genre, related_name="releases", blank=True)
    discogs = models.URLField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)
    catalog_number = models.CharField(max_length=255, blank=True, null=True)

    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    RELEASE_TYPES = [
        ("LP", "LP"),
        ("EP", "EP"),
        ("Single", "Single"),
        ("Box Set", "Box Set"),
    ]
    release_type = models.CharField(
        max_length=255, choices=RELEASE_TYPES, blank=True, null=True
    )

    RECORDING_TYPES = [
        ("Studio", "Studio"),
        ("Live", "Live"),
        ("Studio and Live", "Studio and Live"),
        ("Compilation", "Compilation"),
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

    spotify_url = models.URLField(blank=True, null=True)
    apple_music_url = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

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
            img.save(temp_file, format="WEBP")
            temp_file.seek(0)

            # Generate new name for the webp image
            webp_name = os.path.splitext(self.cover.name)[0] + ".webp"

            # remove the original image
            self.cover.delete(save=False)

            # Save the BytesIO object to the FileField
            self.cover.save(webp_name, ContentFile(temp_file.read()), save=False)

            img.close()
            self.cover.close()

        super().save(*args, **kwargs)

    def model_name(self):
        return "Release"


class ReleaseRole(models.Model):
    release = models.ForeignKey(Release, on_delete=models.CASCADE)
    creator = models.ForeignKey(
        Creator,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_query_name="release_roles",
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    alt_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.release} - {self.alt_name or self.creator.name} - {self.role}"


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
        ("relistened", "Relistened"),
        ("relistening", "Relistening"),
        ("bought", "Bought"),
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
    votes = GenericRelation("discover.Vote")

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

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0

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

    def save(self, *args, **kwargs):
        """
        Override the save method to resize and convert the cover image to webp format.
        """

        # Check if the instance already exists in the database.
        if self.pk:
            old_instance = Podcast.objects.get(pk=self.pk)
            # Check if the cover has been updated.
            if old_instance.cover != self.cover:
                # Delete the old cover.
                old_instance.cover.delete(save=False)

        # Save the instance first, to generate a primary key if needed.
        super().save(*args, **kwargs)

        # Resize and convert cover image to webp format
        if self.cover:
            img = Image.open(self.cover.open(mode="rb"))

            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)

            # Save the image to a BytesIO object in webp format
            temp_file = BytesIO()
            img.save(temp_file, format="WEBP")
            temp_file.seek(0)

            # Generate new name for the webp image
            webp_name = os.path.splitext(self.cover.name)[0] + ".webp"

            # Remove the original image.
            self.cover.delete(save=False)

            # Save the BytesIO object to the FileField.
            self.cover.save(webp_name, ContentFile(temp_file.read()), save=False)

            img.close()
            self.cover.close()

        # Save the instance again to persist the changes.
        super().save(*args, **kwargs)


class ReleaseGroup(models.Model):
    title = models.CharField(max_length=100)
    releases = models.ManyToManyField(
        Release, through="ReleaseInGroup", related_name="release_group"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="releasegroup_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="releasegroup_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:releasegroup_detail", args=[str(self.id)])


class ReleaseInGroup(models.Model):
    release = models.ForeignKey(Release, on_delete=models.CASCADE)
    group = models.ForeignKey(ReleaseGroup, on_delete=models.CASCADE)

    class Meta:
        ordering = ["release__release_date"]

    def __str__(self):
        return f"{self.group.title}: {self.release.title}"


class Audiobook(models.Model):
    """
    A Audiobook entity of an Instance
    """

    # book meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    cover = models.ImageField(upload_to=rename_release_cover, null=True, blank=True)
    cover_sens = models.BooleanField(default=False, null=True, blank=True)
    creators = models.ManyToManyField(
        Creator, through="AudiobookRole", related_name="audiobooks"
    )
    instances = models.ManyToManyField(
        Instance, through="AudiobookInstance", related_name="audiobooks"
    )
    publisher = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        related_name="audiobooks",
        null=True,
        blank=True,
    )
    language = LanguageField(max_length=8, blank=True, null=True)
    release_date = models.TextField(blank=True, null=True)
    wikipedia = models.URLField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # novel, novella, short story, poem, etc.
    format = models.CharField(
        max_length=255, blank=True, null=True
    )  # hardcover, paperback, etc.
    length = models.CharField(
        max_length=255, blank=True, null=True
    )  # e.g. 300 pages, 10:00:00, etc.

    internet_archive_url = models.URLField(max_length=200, blank=True, null=True)
    listencheckin = GenericRelation("ListenCheckIn")

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="audiobooks_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="audiobooks_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:audiobook_detail", args=[str(self.id)])

    def model_name(self):
        return "Audiobook"

    @property
    def checkin_count(self):
        return (
            self.listencheckin_set.count()
        )  # adjust this if your related name is different

    def save(self, *args, **kwargs):
        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Audiobook.objects.get(pk=self.pk)
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
            img.save(temp_file, format="WEBP")
            temp_file.seek(0)

            # Generate new name for the webp image
            webp_name = os.path.splitext(self.cover.name)[0] + ".webp"

            # remove the original image
            self.cover.delete(save=False)

            # Save the BytesIO object to the FileField
            self.cover.save(webp_name, ContentFile(temp_file.read()), save=False)

            img.close()
            self.cover.close()

        # Convert the release_date to a standard format if it's not None or empty
        if self.release_date:
            self.release_date = standardize_date(self.release_date)

        super().save(*args, **kwargs)


class AudiobookRole(models.Model):
    audiobook = models.ForeignKey(Audiobook, on_delete=models.CASCADE)
    creator = models.ForeignKey(
        Creator,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_query_name="book_roles",
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    alt_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.audiobook} - {self.alt_name or self.creator.name} - {self.role}"


class AudiobookInstance(models.Model):
    audiobook = models.ForeignKey(Audiobook, on_delete=models.CASCADE)
    instance = models.ForeignKey(
        Instance, on_delete=models.CASCADE, null=True, blank=True
    )
    order = models.PositiveIntegerField(
        null=True, blank=True, default=1
    )  # Ordering of the works in a book

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.audiobook} - {self.instance} - {self.order}"
