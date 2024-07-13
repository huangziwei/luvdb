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
from django.db.models import Min
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.text import slugify
from PIL import Image
from simple_history.models import HistoricalRecords

from activity_feed.models import Activity
from discover.utils import user_has_upvoted
from entity.models import Company, Creator, LanguageField, Role
from visit.models import Location
from visit.utils import get_location_hierarchy_ids
from write.models import (
    create_mentions_notifications,
    find_mentioned_users,
    handle_tags,
)


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

    # credits: crews and casts
    ## crews
    creators = models.ManyToManyField(
        Creator, through="MovieRole", related_name="movies"
    )
    ## casts
    casts = models.ManyToManyField(
        Creator, through="MovieCast", related_name="movies_cast"
    )
    ## main actors and actresses, only for display purpose
    stars = models.ManyToManyField(Creator, related_name="movies_starred", blank=True)

    # companies
    studios = models.ManyToManyField(Company, related_name="movies")
    distributors = models.ManyToManyField(Company, related_name="movies_distributed")

    # cross-media references
    ## based on
    based_on_litworks = models.ManyToManyField(
        "read.Work", blank=True, related_name="movies"
    )
    based_on_games = models.ManyToManyField(
        "play.Work", blank=True, related_name="movies"
    )
    based_on_movies = models.ManyToManyField(
        "self", blank=True, symmetrical=False, related_name="related_movies"
    )
    based_on_series = models.ManyToManyField(
        "Series", blank=True, related_name="movies"
    )

    ## mentions
    mentioned_litworks = models.ManyToManyField(
        "read.Work", blank=True, related_name="mentioned_in_movies"
    )
    mentioned_litinstances = models.ManyToManyField(
        "read.Instance", blank=True, related_name="mentioned_in_movies"
    )
    mentioned_books = models.ManyToManyField(
        "read.Book", blank=True, related_name="mentioned_in_movies"
    )
    mentioned_periodicals = models.ManyToManyField(
        "read.Periodical", blank=True, related_name="mentioned_in_movies"
    )
    mentioned_issues = models.ManyToManyField(
        "read.Issue", blank=True, related_name="mentioned_in_movies"
    )
    mentioned_gameworks = models.ManyToManyField(
        "play.Work", blank=True, related_name="mentioned_in_movies"
    )
    mentioned_games = models.ManyToManyField(
        "play.Game", blank=True, related_name="mentioned_in_movies"
    )
    mentioned_movies = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="mentioned_in_movies",
    )
    mentioned_series = models.ManyToManyField(
        "watch.Series", blank=True, related_name="mentioned_in_movies"
    )
    mentioned_musicalworks = models.ManyToManyField(
        "listen.Work", blank=True, related_name="mentioned_in_movies"
    )
    mentioned_tracks = models.ManyToManyField(
        "listen.Track", blank=True, related_name="mentioned_in_movies"
    )
    mentioned_releases = models.ManyToManyField(
        "listen.Release", blank=True, related_name="mentioned_in_movies"
    )
    mentioned_locations = models.ManyToManyField(
        "visit.Location", blank=True, related_name="mentioned_in_movies"
    )

    ## soundtracks
    ### official soundtracks (OST) release
    soundtracks = models.ManyToManyField(
        "listen.Release", blank=True, related_name="movies_with_soundtrack"
    )
    ### tracks that are featured in the movie, either in the OST or not
    tracks = models.ManyToManyField(
        "listen.Track", blank=True, related_name="movies_featuring_track"
    )
    theme_songs = models.ManyToManyField(
        "listen.Track",
        blank=True,
        related_name="movies_as_theme_song",
    )
    ending_songs = models.ManyToManyField(
        "listen.Track",
        blank=True,
        related_name="movies_as_ending_song",
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
    official_website = models.URLField(blank=True, null=True)

    filming_locations = models.ManyToManyField(
        "visit.Location", related_name="movies_filmed_here", blank=True
    )
    filming_locations_hierarchy = models.TextField(blank=True, null=True)
    setting_locations = models.ManyToManyField(
        "visit.Location", related_name="movies_set_here", blank=True
    )
    setting_locations_hierarchy = models.TextField(blank=True, null=True)

    watchcheckin = GenericRelation("WatchCheckIn")
    votes = GenericRelation("discover.Vote")

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

        if self.filming_locations.exists():
            filming_locations_hierarchy = []
            for location in self.filming_locations.all():
                filming_locations_hierarchy += get_location_hierarchy_ids(location)
            self.filming_locations_hierarchy = ",".join(
                set(filming_locations_hierarchy)
            )
        if self.setting_locations.exists():
            setting_locations_hierarchy = []
            for location in self.setting_locations.all():
                setting_locations_hierarchy += get_location_hierarchy_ids(location)
            self.setting_locations_hierarchy = ",".join(
                set(setting_locations_hierarchy)
            )

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

    @property
    def earliest_release_date(self):
        return self.region_release_dates.aggregate(Min("release_date"))[
            "release_date__min"
        ]

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0


class MovieReleaseDate(auto_prefetch.Model):
    """
    A Release Date with region of a Movie
    """

    RELEASE_TYPES = [
        ("PREMIERE", "Premiere"),
        ("THEATRICAL", "Theatrical"),
        ("DIGITAL", "Digital"),
        ("PHYSICAL", "Physical"),
        ("TV", "TV"),
        ("OTHER", "Other"),
    ]

    movie = auto_prefetch.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="region_release_dates"
    )
    region = models.CharField(max_length=100, blank=True, null=True)
    release_date = models.CharField(max_length=10, blank=True, null=True)
    notes = models.CharField(max_length=300, blank=True, null=True)
    release_type = models.CharField(
        max_length=10, choices=RELEASE_TYPES, default="THEATRICAL"
    )
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
    stars = models.ManyToManyField(Creator, related_name="series_starred", blank=True)
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

    STATUS_CHOICES = (
        ("continuing", "Continuing"),
        ("season-ended", "Season Ended"),
        ("ended", "Series Ended"),
        ("canceled", "Canceled"),
        ("hiatus", "On Hiatus"),
        ("renewed", "Renewed"),
        ("limbo", "In Limbo"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ended",
        blank=True,
        null=True,
    )

    # Cross-references
    ## Base on
    based_on_litworks = models.ManyToManyField(
        "read.Work", blank=True, related_name="series"
    )
    based_on_games = models.ManyToManyField(
        "play.Work", blank=True, related_name="series"
    )
    based_on_series = models.ManyToManyField(
        "self", blank=True, symmetrical=False, related_name="related_series"
    )
    based_on_movies = models.ManyToManyField(Movie, blank=True, related_name="series")
    ## Soundtracks
    soundtracks = models.ManyToManyField(
        "listen.Release", blank=True, related_name="series_with_soundtrack"
    )  # official soundtracks (OST) release

    imdb = models.URLField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)
    official_website = models.URLField(blank=True, null=True)

    watchcheckin = GenericRelation("WatchCheckIn")
    votes = GenericRelation("discover.Vote")

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

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0


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
    imdb = models.URLField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)

    creators = models.ManyToManyField(
        Creator, through="EpisodeRole", related_name="episodes_role"
    )
    casts = models.ManyToManyField(
        Creator, through="EpisodeCast", related_name="episodes_cast"
    )

    filming_locations = models.ManyToManyField(
        "visit.Location", related_name="episodes_filmed_here", blank=True
    )
    filming_locations_hierarchy = models.TextField(blank=True, null=True)
    setting_locations = models.ManyToManyField(
        "visit.Location", related_name="episodes_set_here", blank=True
    )
    setting_locations_hierarchy = models.TextField(blank=True, null=True)

    votes = GenericRelation("discover.Vote")

    history = HistoricalRecords(inherit=True)

    # based on
    based_on_litworks = models.ManyToManyField(
        "read.Work", blank=True, related_name="adapted_episodes"
    )
    based_on_games = models.ManyToManyField(
        "play.Work", blank=True, related_name="adapted_episodes"
    )
    based_on_series = models.ManyToManyField(
        "watch.Series", blank=True, related_name="adapted_episodes"
    )
    based_on_movies = models.ManyToManyField(
        "watch.Movie", blank=True, related_name="adapted_episodes"
    )

    # mentions
    mentioned_litworks = models.ManyToManyField(
        "read.Work", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_litinstances = models.ManyToManyField(
        "read.Instance", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_books = models.ManyToManyField(
        "read.Book", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_periodicals = models.ManyToManyField(
        "read.Periodical", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_issues = models.ManyToManyField(
        "read.Issue", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_gameworks = models.ManyToManyField(
        "play.Work", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_games = models.ManyToManyField(
        "play.Game", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_movies = models.ManyToManyField(
        "watch.Movie", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_series = models.ManyToManyField(
        "watch.Series", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_musicalworks = models.ManyToManyField(
        "listen.Work", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_tracks = models.ManyToManyField(
        "listen.Track", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_releases = models.ManyToManyField(
        "listen.Release", blank=True, related_name="mentioned_in_episodes"
    )
    mentioned_locations = models.ManyToManyField(
        "visit.Location", blank=True, related_name="mentioned_in_episodes"
    )

    tracks = models.ManyToManyField(
        "listen.Track", blank=True, related_name="episodes_featuring_track"
    )  # tracks that are featured in the movie, either in the OST or not
    theme_songs = models.ManyToManyField(
        "listen.Track",
        blank=True,
        related_name="episodes_as_theme_song",
    )
    ending_songs = models.ManyToManyField(
        "listen.Track",
        blank=True,
        related_name="episodes_as_ending_song",
    )

    notes = models.TextField(blank=True, null=True)

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

    def season_episode_format(self):
        return f"S{self.season:02}E{self.episode:02}"

    def get_absolute_url(self):
        return reverse(
            "episode_detail",
            kwargs={
                "series_id": self.series.id,
                "season": f"{self.season:02}",
                "episode": f"{self.episode:02}",
            },
        )

    def save(self, *args, **kwargs):
        is_new_instance = not self.pk
        if is_new_instance:
            super().save(*args, **kwargs)

        if self.filming_locations.exists():
            filming_locations_hierarchy = []
            for location in self.filming_locations.all():
                filming_locations_hierarchy += get_location_hierarchy_ids(location)
            self.filming_locations_hierarchy = ",".join(
                set(filming_locations_hierarchy)
            )
        if self.setting_locations.exists():
            setting_locations_hierarchy = []
            for location in self.setting_locations.all():
                setting_locations_hierarchy += get_location_hierarchy_ids(location)
            self.setting_locations_hierarchy = ",".join(
                set(setting_locations_hierarchy)
            )

        super().save(*args, **kwargs)

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0


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

    visibility = models.CharField(
        max_length=2,
        choices=Activity.VISIBILITY_CHOICES,
        default=Activity.VISIBILITY_PUBLIC,
    )

    visible_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="visible_watch_checkins", blank=True
    )
    activities = GenericRelation(Activity, related_query_name="watch_checkin_activity")

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

    @property
    def has_voted(self):
        return user_has_upvoted(self.user, self.content_object)

    def model_name(self):
        return "Watch Check-In"

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
                    activity.visibility = self.visibility
                    activity.save()  # This will trigger the update logic in Activity model
                except Activity.DoesNotExist:
                    pass  # Handle the case where the Activity object does not exist

            if is_new or activity is None:
                Activity.objects.create(
                    user=self.user,
                    activity_type="watch-check-in",
                    content_object=self,
                    visibility=self.visibility,
                )

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
