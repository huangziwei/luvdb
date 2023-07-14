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
from read.models import LanguageField
from write.models import create_mentions_notifications, handle_tags


# helpers
def rename_movie_poster(instance, filename):
    _, extension = os.path.splitext(filename)
    unique_id = uuid.uuid4()
    directory_name = (
        f"{slugify(instance.title, allow_unicode=True)}-{instance.release_date}"
    )
    new_name = f"{unique_id}{extension}"
    return os.path.join("posters", directory_name, new_name)


class Studio(Entity):
    history = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    founded_date = models.DateField(blank=True, null=True)
    closed_date = models.DateField(blank=True, null=True)

    def __str__(self):
        if self.location:
            return f"{self.location}: {self.name}"
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, blank=True, null=True)
    romanized_title = models.CharField(max_length=100, blank=True, null=True)
    studios = models.ManyToManyField(Studio, related_name="movies")
    persons = models.ManyToManyField(Person, through="MovieRole", related_name="movies")
    casts = models.ManyToManyField(
        Person, through="MovieCast", related_name="movies_cast"
    )
    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    description = models.TextField(blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    poster = models.ImageField(upload_to=rename_movie_poster, null=True, blank=True)
    poster_sens = models.BooleanField(default=False, null=True, blank=True)
    box_office = models.CharField(max_length=20, blank=True, null=True)
    duration = models.CharField(max_length=10, blank=True, null=True)
    languages = LanguageField(blank=True, null=True)
    # genres = models.ManyToManyField("Genre", related_name="movies", blank=True)

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="movies_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="movies_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Movie.objects.get(pk=self.pk)
            # If the poster has been updated
            if old_instance.poster != self.poster:
                # Delete the old poster
                old_instance.poster.delete(save=False)

        super().save(*args, **kwargs)

        if self.poster:
            img = Image.open(self.poster.open(mode="rb"))

            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)

                # Save the image to a BytesIO object
                temp_file = BytesIO()
                img.save(temp_file, format=img.format)
                temp_file.seek(0)

                # Save the BytesIO object to the FileField
                self.poster.save(
                    self.poster.name, ContentFile(temp_file.read()), save=False
                )

            img.close()
            self.poster.close()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("watch:movie_detail", args=[str(self.id)])


class MovieRole(models.Model):
    """
    A Role of a Person in a Movie
    """

    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="movieroles"
    )
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    alt_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.movie} - {self.person} - {self.role}"


class MovieCast(models.Model):
    """
    A Cast in a Game
    """

    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="moviecasts"
    )
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    character_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.movie} - {self.person} - {self.role}"


class Series(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, blank=True, null=True)
    romanized_title = models.CharField(max_length=100, blank=True, null=True)
    studios = models.ManyToManyField(Studio, related_name="series")
    persons = models.ManyToManyField(
        Person, through="SeriesRole", related_name="series"
    )
    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    description = models.TextField(blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    poster = models.ImageField(upload_to=rename_movie_poster, null=True, blank=True)
    poster_sens = models.BooleanField(default=False, null=True, blank=True)
    duration = models.CharField(max_length=10, blank=True, null=True)
    languages = LanguageField(blank=True, null=True)
    # genres = models.ManyToManyField("Genre", related_name="series", blank=True)

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="watch_series_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="watch_series_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Series.objects.get(pk=self.pk)
            # If the poster has been updated
            if old_instance.poster != self.poster:
                # Delete the old poster
                old_instance.poster.delete(save=False)

        super().save(*args, **kwargs)

        if self.poster:
            img = Image.open(self.poster.open(mode="rb"))

            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)

                # Save the image to a BytesIO object
                temp_file = BytesIO()
                img.save(temp_file, format=img.format)
                temp_file.seek(0)

                # Save the BytesIO object to the FileField
                self.poster.save(
                    self.poster.name, ContentFile(temp_file.read()), save=False
                )

            img.close()
            self.poster.close()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("watch:series_detail", args=[str(self.id)])


class SeriesRole(models.Model):
    """
    A Role of a Person in a Movie
    """

    series = models.ForeignKey(
        Series, on_delete=models.CASCADE, related_name="seriesroles"
    )
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    alt_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.series} - {self.person} - {self.role}"


class Episode(models.Model):
    series = models.ForeignKey(
        Series, on_delete=models.CASCADE, related_name="episodes"
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    romanized_title = models.CharField(max_length=255, blank=True, null=True)
    season = models.IntegerField(blank=True, null=True)
    episode = models.IntegerField(blank=True, null=True)
    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    persons = models.ManyToManyField(
        Person, through="EpisodeRole", related_name="episodes_role"
    )
    casts = models.ManyToManyField(
        Person, through="EpisodeCast", related_name="episodes_cast"
    )

    def __str__(self):
        return f"{self.series.title} - Season {self.season} - Episode {self.episode}"

    def get_absolute_url(self):
        return reverse("watch:episode_detail", args=[str(self.series.id), str(self.id)])


class EpisodeRole(models.Model):
    """
    A Role of a Person in a Movie
    """

    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="episodesroles"
    )
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    alt_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.episode} - {self.person} - {self.role}"


class EpisodeCast(models.Model):
    """
    A Cast in a Game
    """

    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE, related_name="episodecasts"
    )
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    character_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.episode} - {self.person} - {self.role}"


class WatchCheckIn(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    WATCHING_STATUS_CHOICES = [
        ("to_watch", "To Watch"),
        ("watching", "Watching"),
        ("watched", "Watched"),
        ("paused", "Paused"),
        ("abandoned", "Abandoned"),
        ("rewatching", "Rewatching"),
        ("rewatched", "Rewatched"),
    ]
    status = models.CharField(max_length=255, choices=WATCHING_STATUS_CHOICES)
    share_to_feed = models.BooleanField(default=False)
    content = models.TextField(
        null=True, blank=True
    )  # Any thoughts or comments at this check-in.
    timestamp = models.DateTimeField(auto_now_add=True)
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

    def get_absolute_url(self):
        return reverse("watch:watch_checkin_detail", args=[str(self.id)])

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="watchcheckin", object_id=self.id
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
                activity_type="watch-check-in",
                content_object=self,
            )
        else:
            print("Not creating activity")
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)
