import os
import uuid
from io import BytesIO

import auto_prefetch
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from PIL import Image
from simple_history.models import HistoricalRecords

from activity_feed.models import Activity
from discover.utils import user_has_upvoted
from entity.models import Company, CoverAlbum, CoverImage, Creator, LanguageField, Role
from read.models import Instance, standardize_date
from write.models import (
    create_mentions_notifications,
    find_mentioned_users,
    handle_tags,
)


# helpers
def rename_release_cover(instance, filename):
    if filename is None:
        filename = "default.jpg"
    _, extension = os.path.splitext(filename)
    unique_id = uuid.uuid4()

    # Ensure we're working with the correct related object
    if isinstance(instance, CoverImage):
        related_object = instance.cover_album.content_object
    else:
        related_object = instance

    if not hasattr(related_object, "title"):
        raise ValueError("rename_release_cover requires an object with a title.")

    base_name = slugify(related_object.title, allow_unicode=True)

    # Check if the instance has a release_date attribute
    if hasattr(related_object, "release_date") and related_object.release_date:
        directory_name = f"{base_name}-{related_object.release_date}"
    else:
        directory_name = base_name

    new_name = f"{unique_id}{extension}"
    return os.path.join("covers", directory_name, new_name)


class Genre(auto_prefetch.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Work(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # musical work meta data
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True, null=True)
    other_titles = models.TextField(blank=True, null=True)
    creators = models.ManyToManyField(
        Creator, through="WorkRole", related_name="listen_works"
    )
    release_date = models.CharField(max_length=10, blank=True, null=True)
    recorded_date = models.CharField(max_length=10, blank=True, null=True)
    genres = models.ManyToManyField(Genre, related_name="listen_works", blank=True)
    wikipedia = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="musicwork_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="musicwork_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:work_detail", kwargs={"pk": self.pk})


class WorkRole(auto_prefetch.Model):
    work = auto_prefetch.ForeignKey(Work, on_delete=models.CASCADE)
    creator = auto_prefetch.ForeignKey(
        Creator,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="listen_workrole_set",
    )
    role = auto_prefetch.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="listen_workrole_set",
    )
    alt_name = models.CharField(max_length=255, blank=True, null=True)
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.role} of {self.work} by {self.creator}"


class Track(auto_prefetch.Model):
    """
    A Work entity
    """

    # admin
    locked = models.BooleanField(default=False)

    # track meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    other_titles = models.TextField(blank=True, null=True)
    creators = models.ManyToManyField(
        Creator, through="TrackRole", related_name="tracks"
    )
    work = auto_prefetch.ForeignKey(
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
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="tracks_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="tracks_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:track_detail", kwargs={"pk": self.pk})


class TrackRole(auto_prefetch.Model):
    track = auto_prefetch.ForeignKey(Track, on_delete=models.CASCADE)
    creator = auto_prefetch.ForeignKey(
        Creator, on_delete=models.CASCADE, null=True, blank=True
    )
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )
    alt_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.track} - {self.alt_name or self.creator.name} - {self.role}"


# Release
class Release(auto_prefetch.Model):
    """
    An Release Entity
    """

    # admin
    locked = models.BooleanField(default=False)

    # Release cover
    cover = models.ImageField(upload_to=rename_release_cover, null=True, blank=True)
    cover_album = GenericRelation(CoverAlbum, related_query_name="release")
    cover_sens = models.BooleanField(default=False, null=True, blank=True)

    # Release meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
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
        ("Soundtrack", "Soundtrack"),
        ("Mixtape", "Mixtape"),
        ("Demo", "Demo"),
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
    internet_archive_url = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Entry metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="releases_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="releases_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)
    listencheckin = GenericRelation("ListenCheckIn")
    votes = GenericRelation("discover.Vote")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:release_detail", kwargs={"pk": self.pk})

    def get_genres(self):
        genres = set()
        for track in self.tracks.all():
            genres.update(track.genres.all())
        return genres

    def save(self, *args, **kwargs):
        # To hold a flag indicating if the cover is new or updated
        new_or_updated_cover = False

        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Release.objects.get(pk=self.pk)
            # If the cover has been updated
            if old_instance.cover != self.cover:
                # Delete the old cover
                old_instance.cover.delete(save=False)
                new_or_updated_cover = True
        else:
            new_or_updated_cover = True

        super().save(*args, **kwargs)

        if new_or_updated_cover and self.cover:
            # Ensure CoverAlbum exists for this book
            cover_album, created = CoverAlbum.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Release),
                object_id=self.id,
            )

            # Check if the new cover already exists in CoverAlbum
            existing_cover = cover_album.images.filter(image=self.cover).first()

            if existing_cover:
                # If the cover already exists, mark it as primary
                existing_cover.is_primary = True
                existing_cover.save()
            else:
                # Otherwise, add the new cover and mark it as primary
                CoverImage.objects.create(cover_album=cover_album, image=self.cover)
                # cover_image.save()
                

        super().save(*args, **kwargs)

    def model_name(self):
        return "Release"

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0


class ReleaseRole(auto_prefetch.Model):
    release = auto_prefetch.ForeignKey(Release, on_delete=models.CASCADE)
    creator = auto_prefetch.ForeignKey(
        Creator,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_query_name="release_roles",
    )
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )
    alt_name = models.CharField(max_length=255, blank=True, null=True)
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.release} - {self.alt_name or self.creator.name} - {self.role}"


class ReleaseTrack(auto_prefetch.Model):
    release = auto_prefetch.ForeignKey(Release, on_delete=models.CASCADE)
    track = auto_prefetch.ForeignKey(
        Track, on_delete=models.CASCADE, null=True, blank=True
    )
    alt_title = models.CharField(max_length=255, blank=True, null=True)
    disk = models.CharField(max_length=10, default="1", blank=True, null=True)
    order = models.PositiveIntegerField(default=1, null=True, blank=True)
    history = HistoricalRecords(inherit=True)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["disk", "order"]

    def __str__(self):
        return f"{self.release.title}, {self.track.title}"


class ListenCheckIn(auto_prefetch.Model):
    content_type = auto_prefetch.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    user = auto_prefetch.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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
    updated_at = models.DateTimeField(auto_now=True)
    progress = models.CharField(max_length=20, null=True, blank=True)
    TOTAL_LISTEN_TIME = "TT"
    LOOP_TIME = "LT"
    EPISODE = "EP"
    TRACK = "TR"
    PROGRESS_TYPE_CHOICES = [
        (TOTAL_LISTEN_TIME, "Accumulated Listen Time"),
        (LOOP_TIME, "Loop Time"),
        (EPISODE, "Episode"),
        (TRACK, "Track"),
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

    visibility = models.CharField(
        max_length=2,
        choices=Activity.VISIBILITY_CHOICES,
        default=Activity.VISIBILITY_PUBLIC,
    )

    visible_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="visible_listen_checkins", blank=True
    )
    activities = GenericRelation(Activity, related_query_name="listen_checkin_activity")

    def get_absolute_url(self):
        return reverse(
            "write:listen_checkin_detail",
            kwargs={"pk": self.pk, "username": self.user.username},
        )

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

    @property
    def has_voted(self):
        return user_has_upvoted(self.user, self.content_object)

    def model_name(self):
        return "Listen Check-In"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        was_updated = False
        super().save(*args, **kwargs)

        visible_to_users = set()

        if self.visibility == Activity.VISIBILITY_MENTIONED:
            visible_to_users.update(find_mentioned_users(self.content))
        elif self.visibility == Activity.VISIBILITY_FOLLOWERS:
            visible_to_users.update(
                self.user.followers.values_list("follower_id", flat=True)
            )
        elif self.visibility == Activity.VISIBILITY_PRIVATE:
            visible_to_users.add(self.user.id)

        # Always include self.user
        visible_to_users.add(self.user.id)

        self.visible_to.set(visible_to_users)

        # Attempt to fetch an existing Activity object for this check-in
        try:
            activity = Activity.objects.get(
                content_type__model="listencheckin", object_id=self.id
            )
        except Activity.DoesNotExist:
            activity = None

        # Conditionally create an Activity object
        if self.share_to_feed:
            if not is_new:
                # Check if updated
                was_updated = self.updated_at > self.timestamp

            if was_updated:
                # Fetch and update the related Activity object
                try:
                    activity = Activity.objects.get(
                        content_type__model="listencheckin", object_id=self.id
                    )
                    activity.save()  # This will trigger the update logic in Activity model
                except Activity.DoesNotExist:
                    pass  # Handle the case where the Activity object does not exist

            if is_new or activity is None:
                Activity.objects.create(
                    user=self.user,
                    activity_type="listen-check-in",
                    content_object=self,
                )
        elif activity is not None:
            # Optionally, remove the Activity if share_to_feed is False
            activity.delete()

        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


class Podcast(auto_prefetch.Model):
    """
    A Podcast Entity
    """

    # admin
    locked = models.BooleanField(default=False)

    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    cover = models.ImageField(upload_to=rename_release_cover, null=True, blank=True)
    cover_album = GenericRelation(CoverAlbum, related_query_name="podcast")

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
    votes = GenericRelation("discover.Vote")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:podcast_detail", kwargs={"pk": self.pk})

    def model_name(self):
        return "Podcast"

    def save(self, *args, **kwargs):
        # To hold a flag indicating if the cover is new or updated
        new_or_updated_cover = False

        # Check if the instance already exists in the database.
        if self.pk:
            old_instance = Podcast.objects.get(pk=self.pk)
            # Check if the cover has been updated.
            if old_instance.cover != self.cover:
                # Delete the old cover.
                old_instance.cover.delete(save=False)
                new_or_updated_cover = True
        else:
            new_or_updated_cover = True

        # Save the instance first, to generate a primary key if needed.
        super().save(*args, **kwargs)

        # Resize and convert cover image to webp format
        if new_or_updated_cover and self.cover:
            # Ensure CoverAlbum exists for this book
            cover_album, created = CoverAlbum.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Podcast),
                object_id=self.id,
            )

            # Check if the new cover already exists in CoverAlbum
            existing_cover = cover_album.images.filter(image=self.cover).first()

            if existing_cover:
                # If the cover already exists, mark it as primary
                existing_cover.is_primary = True
                existing_cover.save()
            else:
                # Otherwise, add the new cover and mark it as primary
                CoverImage.objects.create(cover_album=cover_album, image=self.cover)
                # cover_image.save()
                
        # Save the instance again to persist the changes.
        super().save(*args, **kwargs)

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0


class ReleaseGroup(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # release group meta
    title = models.CharField(max_length=100)
    releases = models.ManyToManyField(
        Release, through="ReleaseInGroup", related_name="release_group"
    )

    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="releasegroup_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="releasegroup_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:releasegroup_detail", args=[str(self.id)])


class ReleaseInGroup(auto_prefetch.Model):
    release = auto_prefetch.ForeignKey(Release, on_delete=models.CASCADE)
    group = auto_prefetch.ForeignKey(ReleaseGroup, on_delete=models.CASCADE)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["release__release_date"]

    def __str__(self):
        return f"{self.group.title}: {self.release.title}"


class Audiobook(auto_prefetch.Model):
    """
    A Audiobook entity of an Instance
    """

    # admin
    locked = models.BooleanField(default=False)

    # audiobook meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    cover = models.ImageField(upload_to=rename_release_cover, null=True, blank=True)
    cover_sens = models.BooleanField(default=False, null=True, blank=True)
    cover_album = GenericRelation(CoverAlbum, related_query_name="audiobook")

    creators = models.ManyToManyField(
        Creator, through="AudiobookRole", related_name="audiobooks"
    )
    instances = models.ManyToManyField(
        Instance, through="AudiobookInstance", related_name="audiobooks"
    )
    publisher = auto_prefetch.ForeignKey(
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
    votes = GenericRelation("discover.Vote")

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="audiobooks_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="audiobooks_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listen:audiobook_detail", args=[str(self.id)])

    def model_name(self):
        return "Audiobook"

    def get_genres(self):
        genres = set()
        for instance in self.instances.all():
            if instance.work:
                genres.update(instance.work.genres.all())
        return genres

    @property
    def checkin_count(self):
        return (
            self.listencheckin_set.count()
        )  # adjust this if your related name is different

    def save(self, *args, **kwargs):
        # To hold a flag indicating if the cover is new or updated
        new_or_updated_cover = False
        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Audiobook.objects.get(pk=self.pk)
            # If the cover has been updated
            if old_instance.cover != self.cover:
                # Delete the old cover
                old_instance.cover.delete(save=False)
                new_or_updated_cover = True
        else:
            new_or_updated_cover = True

        super().save(*args, **kwargs)

        if new_or_updated_cover and self.cover:
            # Ensure CoverAlbum exists for this book
            cover_album, created = CoverAlbum.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Audiobook),
                object_id=self.id,
            )

            # Check if the new cover already exists in CoverAlbum
            existing_cover = cover_album.images.filter(image=self.cover).first()

            if existing_cover:
                # If the cover already exists, mark it as primary
                existing_cover.is_primary = True
                existing_cover.save()
            else:
                # Otherwise, add the new cover and mark it as primary
                CoverImage.objects.create(cover_album=cover_album, image=self.cover)
                # cover_image.save()

        # Convert the release_date to a standard format if it's not None or empty
        if self.release_date:
            self.release_date = standardize_date(self.release_date)

        super().save(*args, **kwargs)

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0


class AudiobookRole(auto_prefetch.Model):
    audiobook = auto_prefetch.ForeignKey(Audiobook, on_delete=models.CASCADE)
    creator = auto_prefetch.ForeignKey(
        Creator,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_query_name="book_roles",
    )
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )
    alt_name = models.CharField(max_length=255, blank=True, null=True)
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.audiobook} - {self.alt_name or self.creator.name} - {self.role}"


class AudiobookInstance(auto_prefetch.Model):
    audiobook = auto_prefetch.ForeignKey(Audiobook, on_delete=models.CASCADE)
    instance = auto_prefetch.ForeignKey(
        Instance, on_delete=models.CASCADE, null=True, blank=True
    )
    order = models.PositiveIntegerField(
        null=True, blank=True, default=1
    )  # Ordering of the works in a book

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["order"]

    def __str__(self):
        return f"{self.audiobook} - {self.instance} - {self.order}"
