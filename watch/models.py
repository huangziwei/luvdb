import os
import uuid
from io import BytesIO

import auto_prefetch
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from PIL import Image
from simple_history.models import HistoricalRecords

from activity_feed.models import Activity
from entity.models import Company, Creator, LanguageField, Role
from read.models import Work as LitWork
from write.models import create_mentions_notifications, handle_tags
from write.utils_bluesky import create_bluesky_post
from write.utils_mastodon import create_mastodon_post


# helpers
def rename_movie_poster(instance, filename):
    if filename is None:
        filename = "default.jpg"
    _, extension = os.path.splitext(filename)
    unique_id = uuid.uuid4()
    directory_name = f"{slugify(instance.title, allow_unicode=True)}"
    new_name = f"{unique_id}{extension}"
    return os.path.join("posters", directory_name, new_name)


class Genre(auto_prefetch.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Movie(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # movie meta data
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, blank=True, null=True)
    other_titles = models.TextField(blank=True, null=True)
    studios = models.ManyToManyField(Company, related_name="movies")
    distributors = models.ManyToManyField(Company, related_name="movies_distributed")
    creators = models.ManyToManyField(
        Creator, through="MovieRole", related_name="movies"
    )
    casts = models.ManyToManyField(
        Creator, through="MovieCast", related_name="movies_cast"
    )
    based_on = auto_prefetch.ForeignKey(
        LitWork, on_delete=models.CASCADE, null=True, blank=True, related_name="movies"
    )

    notes = models.TextField(blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    poster = models.ImageField(upload_to=rename_movie_poster, null=True, blank=True)
    poster_sens = models.BooleanField(default=False, null=True, blank=True)
    box_office = models.CharField(max_length=20, blank=True, null=True)
    duration = models.CharField(max_length=10, blank=True, null=True)
    languages = LanguageField(blank=True, null=True)
    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)
    imdb = models.URLField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)

    watchcheckin = GenericRelation("WatchCheckIn")

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="movies_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="movies_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        new_or_updated_cover = False
        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Movie.objects.get(pk=self.pk)
            # If the poster has been updated
            if old_instance.poster != self.poster:
                # Delete the old poster
                old_instance.poster.delete(save=False)
                new_or_updated_cover = True
        else:
            new_or_updated_cover = True

        super().save(*args, **kwargs)

        if new_or_updated_cover and self.poster:
            img = Image.open(self.poster.open(mode="rb"))

            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)

            # Save the image to a BytesIO object
            temp_file = BytesIO()
            img.save(temp_file, format="WEBP")
            temp_file.seek(0)

            # Generate new name for the webp image
            webp_name = os.path.splitext(self.poster.name)[0] + ".webp"

            # remove the original image
            self.poster.delete(save=False)

            # Save the BytesIO object to the FileField
            self.poster.save(webp_name, ContentFile(temp_file.read()), save=False)

            img.close()
            self.poster.close()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("watch:movie_detail", args=[str(self.id)])

    def model_name(self):
        return "Movie"


class MovieReleaseDate(auto_prefetch.Model):
    """
    A Release Date with region of a Movie
    """

    movie = auto_prefetch.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="region_release_dates"
    )
    region = models.CharField(max_length=100, blank=True, null=True)
    release_date = models.CharField(max_length=10, blank=True, null=True)
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.movie} - {self.region} - {self.release_date}"


class MovieRole(auto_prefetch.Model):
    """
    A Role of a Creator in a Movie
    """

    movie = auto_prefetch.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="movieroles"
    )
    creator = auto_prefetch.ForeignKey(
        Creator, on_delete=models.CASCADE, null=True, blank=True
    )
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )
    alt_name = models.CharField(max_length=100, blank=True, null=True)
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.movie} - {self.creator} - {self.role}"


class MovieCast(auto_prefetch.Model):
    """
    A Cast in a Game
    """

    movie = auto_prefetch.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="moviecasts"
    )
    creator = auto_prefetch.ForeignKey(
        Creator, on_delete=models.CASCADE, null=True, blank=True
    )
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )
    character_name = models.CharField(max_length=100, blank=True, null=True)
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.movie} - {self.creator} - {self.role}"


class Series(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # series meta data
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, blank=True, null=True)
    other_titles = models.TextField(blank=True, null=True)
    studios = models.ManyToManyField(Company, related_name="series")
    distributors = models.ManyToManyField(Company, related_name="series_distributed")
    creators = models.ManyToManyField(
        Creator, through="SeriesRole", related_name="series"
    )
    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    notes = models.TextField(blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    poster = models.ImageField(upload_to=rename_movie_poster, null=True, blank=True)
    poster_sens = models.BooleanField(default=False, null=True, blank=True)
    duration = models.CharField(max_length=10, blank=True, null=True)
    languages = LanguageField(blank=True, null=True)
    genres = models.ManyToManyField(Genre, related_name="series", blank=True)
    based_on = auto_prefetch.ForeignKey(
        LitWork, on_delete=models.CASCADE, null=True, blank=True, related_name="series"
    )
    imdb = models.URLField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)
    watchcheckin = GenericRelation("WatchCheckIn")
    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="watch_series_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="watch_series_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        new_or_updated_cover = False
        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Series.objects.get(pk=self.pk)
            # If the poster has been updated
            if old_instance.poster != self.poster:
                # Delete the old poster
                old_instance.poster.delete(save=False)
                new_or_updated_cover = True
        else:
            new_or_updated_cover = True

        super().save(*args, **kwargs)

        if new_or_updated_cover and self.poster:
            img = Image.open(self.poster.open(mode="rb"))

            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)

            # Save the image to a BytesIO object
            temp_file = BytesIO()
            img.save(temp_file, format="WEBP")
            temp_file.seek(0)

            # Generate new name for the webp image
            webp_name = os.path.splitext(self.poster.name)[0] + ".webp"

            # remove the original image
            self.poster.delete(save=False)

            # Save the BytesIO object to the FileField
            self.poster.save(webp_name, ContentFile(temp_file.read()), save=False)

            img.close()
            self.poster.close()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("watch:series_detail", args=[str(self.id)])

    def model_name(self):
        return "Series"


class SeriesRole(auto_prefetch.Model):
    """
    A Role of a Creator in a Movie
    """

    series = auto_prefetch.ForeignKey(
        Series, on_delete=models.CASCADE, related_name="seriesroles"
    )
    creator = auto_prefetch.ForeignKey(
        Creator, on_delete=models.CASCADE, null=True, blank=True
    )
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )
    alt_name = models.CharField(max_length=100, blank=True, null=True)
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.series} - {self.creator} - {self.role}"


class Episode(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # episode meta data
    series = auto_prefetch.ForeignKey(
        Series, on_delete=models.CASCADE, related_name="episodes"
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    other_titles = models.TextField(blank=True, null=True)
    season = models.IntegerField(blank=True, null=True)
    episode = models.IntegerField(blank=True, null=True)
    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    length = models.CharField(max_length=10, blank=True, null=True)  # in minutes
    creators = models.ManyToManyField(
        Creator, through="EpisodeRole", related_name="episodes_role"
    )
    casts = models.ManyToManyField(
        Creator, through="EpisodeCast", related_name="episodes_cast"
    )
    history = HistoricalRecords(inherit=True)

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="episodes_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="episodes_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return f"{self.series.title} - Season {self.season} - Episode {self.episode}"

    def get_absolute_url(self):
        return reverse("watch:episode_detail", args=[str(self.series.id), str(self.id)])


class EpisodeRole(auto_prefetch.Model):
    """
    A Role of a Creator in a Movie
    """

    episode = auto_prefetch.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="episoderoles"
    )
    creator = auto_prefetch.ForeignKey(
        Creator, on_delete=models.CASCADE, null=True, blank=True
    )
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )
    alt_name = models.CharField(max_length=100, blank=True, null=True)
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.episode} - {self.creator} - {self.role}"


class EpisodeCast(auto_prefetch.Model):
    """
    A Cast in a Game
    """

    episode = auto_prefetch.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="episodecasts"
    )
    creator = auto_prefetch.ForeignKey(
        Creator, on_delete=models.CASCADE, null=True, blank=True
    )
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )
    character_name = models.CharField(max_length=100, blank=True, null=True)
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.episode} - {self.creator} - {self.role}"


class WatchCheckIn(auto_prefetch.Model):
    content_type = auto_prefetch.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    user = auto_prefetch.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    STATUS_CHOICES = [
        ("to_watch", "To Watch"),
        ("watching", "Watching"),
        ("watched", "Watched"),
        ("paused", "Paused"),
        ("abandoned", "Abandoned"),
        ("rewatching", "Rewatching"),
        ("rewatched", "Rewatched"),
        ("Afterthoughts", "Afterthoughts"),
    ]
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
    share_to_feed = models.BooleanField(default=False)
    content = models.TextField(
        null=True, blank=True
    )  # Any thoughts or comments at this check-in.
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    progress = models.CharField(max_length=20, null=True, blank=True)
    TIME = "TM"
    EPISODE = "EP"
    PROGRESS_TYPE_CHOICES = [
        (TIME, "Time(s)"),
        (EPISODE, "Episode"),
    ]
    progress_type = models.CharField(
        max_length=2,
        choices=PROGRESS_TYPE_CHOICES,
        default=TIME,
    )
    comments = GenericRelation("write.Comment")
    comments_enabled = models.BooleanField(default=True)
    tags = models.ManyToManyField("write.Tag", blank=True)
    reposts = GenericRelation("write.Repost")
    votes = GenericRelation("discover.Vote")

    def get_absolute_url(self):
        return reverse(
            "write:watch_checkin_detail",
            kwargs={"pk": self.pk, "username": self.user.username},
        )

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="watchcheckin", object_id=self.id
            )
            return activity.id
        except ObjectDoesNotExist:
            return None

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0

    def model_name(self):
        return "Watch Check-In"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        was_updated = False
        super().save(*args, **kwargs)
        # Attempt to fetch an existing Activity object for this check-in
        try:
            activity = Activity.objects.get(
                content_type__model="watchcheckin", object_id=self.id
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
                        content_type__model="watchcheckin", object_id=self.id
                    )
                    activity.save()  # This will trigger the update logic in Activity model
                except Activity.DoesNotExist:
                    pass  # Handle the case where the Activity object does not exist

            if is_new or activity is None:
                Activity.objects.create(
                    user=self.user,
                    activity_type="watch-check-in",
                    content_object=self,
                )

                if hasattr(self.user, "bluesky_account"):
                    try:
                        bluesky_account = self.user.bluesky_account
                        create_bluesky_post(
                            bluesky_account.bluesky_handle,
                            bluesky_account.bluesky_pds_url,
                            bluesky_account.get_bluesky_app_password(),  # Ensure this method securely retrieves the password
                            f'I checked in to "{self.content_object.title}" on LʌvDB\n\n'
                            + self.content
                            + "\n\n",
                            self.id,
                            self.user.username,
                            "WatchCheckIn",
                        )
                    except Exception as e:
                        print(f"Error creating Bluesky post: {e}")

                if hasattr(self.user, "mastodon_account"):
                    try:
                        mastodon_account = self.user.mastodon_account
                        create_mastodon_post(
                            mastodon_account.mastodon_handle,
                            mastodon_account.get_mastodon_access_token(),  # Ensure this method securely retrieves the password
                            f'I checked in to "{self.content_object.title}" on LʌvDB\n\n'
                            + self.content
                            + "\n\n",
                            self.id,
                            self.user.username,
                            "WatchCheckIn",
                        )
                    except Exception as e:
                        print(f"Error creating Mastodon post: {e}")

        elif activity is not None:
            # Optionally, remove the Activity if share_to_feed is False
            activity.delete()
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


class Collection(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # collection meta data
    title = models.CharField(max_length=100)
    notes = models.TextField(null=True, blank=True)

    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="collection_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="collection_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("watch:collection_detail", args=[str(self.id)])


class ContentInCollection(auto_prefetch.Model):
    collection = auto_prefetch.ForeignKey(
        Collection, related_name="contents", on_delete=models.CASCADE
    )
    order = models.PositiveIntegerField(null=True, blank=True)

    content_type = auto_prefetch.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    comment = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["order"]

    def __str__(self):
        return f"{self.collection.title}: {self.content_object}"
