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
from entity.models import Company, Creator, Entity, Role
from visit.models import Location
from visit.utils import get_location_hierarchy_ids
from write.models import create_mentions_notifications, handle_tags
from write.utils_bluesky import create_bluesky_post
from write.utils_mastodon import create_mastodon_post


# helpers
def rename_game_cover(instance, filename):
    if filename is None:
        filename = "default.jpg"
    _, extension = os.path.splitext(filename)
    unique_id = uuid.uuid4()
    directory_name = f"{slugify(instance.title, allow_unicode=True)}"
    new_name = f"{unique_id}{extension}"
    return os.path.join("covers", directory_name, new_name)


class Platform(Entity):
    website = models.URLField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)
    release_date = models.CharField(max_length=10, blank=True, null=True)
    discontinued_date = models.CharField(max_length=10, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Genre(auto_prefetch.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Work(auto_prefetch.Model):  # Renamed from Book
    """
    A Work entity
    """

    # admin
    locked = models.BooleanField(default=False)

    # work meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    other_titles = models.TextField(blank=True, null=True)
    creators = models.ManyToManyField(
        Creator, through="WorkRole", related_name="play_works"
    )

    developers = models.ManyToManyField(Company, related_name="play_works")

    first_release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD

    WORK_TYPES = (
        ("visual_novel", "Visual Novel"),
        ("rpg", "RPG"),
        ("action", "Action"),
        ("adventure", "Adventure"),
        ("platformer", "Platformer"),
        ("puzzle", "Puzzle"),
        ("racing", "Racing"),
        ("fps", "FPS"),
        ("tbs", "TBS"),
        ("rts", "RTS"),
        ("sports", "Sports"),
        ("simulation", "Simulation"),
        ("strategy", "Strategy"),
        ("mmorpg", "MMORPG"),
        ("sandbox", "Sandbox"),
        ("other", "Other"),
    )
    work_type = models.CharField(
        max_length=255, choices=WORK_TYPES, blank=True, null=True
    )
    setting_locations = models.ManyToManyField(
        Location, related_name="games_set_here", blank=True
    )
    setting_locations_hierarchy = models.TextField(blank=True, null=True)

    genres = models.ManyToManyField(Genre, related_name="play_works", blank=True)
    wikipedia = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    based_on_games = models.ManyToManyField(
        "self", blank=True, symmetrical=False, related_name="related_games"
    )
    based_on_litworks = models.ManyToManyField(
        "read.Work", blank=True, related_name="games"
    )
    based_on_movies = models.ManyToManyField(
        "watch.Movie", blank=True, related_name="games"
    )
    based_on_series = models.ManyToManyField(
        "watch.Series", blank=True, related_name="games"
    )

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="play_works_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="play_works_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("play:work_detail", kwargs={"pk": self.pk})

    def model_name(self):
        return "GameWork"

    def save(self, *args, **kwargs):
        is_new_instance = not self.pk
        if is_new_instance:
            super().save(*args, **kwargs)
        if self.setting_locations.exists():
            setting_locations_hierarchy = []
            for location in self.setting_locations.all():
                setting_locations_hierarchy += get_location_hierarchy_ids(location)
            self.setting_locations_hierarchy = ",".join(
                set(setting_locations_hierarchy)
            )

        super().save(*args, **kwargs)


class WorkRole(auto_prefetch.Model):  # Renamed from BookRole
    """
    A Role of a Creator in a Work
    """

    work = auto_prefetch.ForeignKey(Work, on_delete=models.CASCADE)
    creator = auto_prefetch.ForeignKey(
        Creator,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="play_workrole_set",
    )
    role = auto_prefetch.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="play_workrole_set",
    )
    alt_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.work} - {self.creator} - {self.role}"


class Game(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # game meta data
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, blank=True, null=True)
    other_titles = models.TextField(blank=True, null=True)
    work = auto_prefetch.ForeignKey(
        Work, on_delete=models.CASCADE, null=True, blank=True, related_name="games"
    )

    developers = models.ManyToManyField(Company, related_name="developed_games")
    publishers = models.ManyToManyField(Company, related_name="published_games")

    creators = models.ManyToManyField(Creator, through="GameRole", related_name="games")
    casts = models.ManyToManyField(
        Creator, through="GameCast", related_name="games_cast"
    )
    notes = models.TextField(blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    cover = models.ImageField(upload_to=rename_game_cover, null=True, blank=True)
    cover_sens = models.BooleanField(default=False, null=True, blank=True)
    price = models.CharField(max_length=20, blank=True, null=True)
    platforms = models.ManyToManyField(Platform, related_name="games")
    rating = models.TextField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)
    playcheckin = GenericRelation("PlayCheckIn")

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="games_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="games_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # To hold a flag indicating if the cover is new or updated
        new_or_updated_cover = False

        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Game.objects.get(pk=self.pk)
            # If the cover has been updated
            if old_instance.cover != self.cover:
                # Delete the old cover
                old_instance.cover.delete(save=False)
                new_or_updated_cover = True
        else:
            new_or_updated_cover = True

        super().save(*args, **kwargs)

        if new_or_updated_cover and self.cover:
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

    def get_absolute_url(self):
        return reverse("play:game_detail", args=[str(self.id)])

    def model_name(self):
        return "Game"

    @property
    def earliest_release_date(self):
        try:
            return self.region_release_dates.order_by("release_date")[0].release_date
        except IndexError:
            return None


class GameReleaseDate(auto_prefetch.Model):
    """
    A Release Date with region of a Game
    """

    game = auto_prefetch.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="region_release_dates"
    )
    region = models.CharField(max_length=100, blank=True, null=True)
    release_date = models.CharField(max_length=10, blank=True, null=True)
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.game} - {self.region} - {self.release_date}"


class GameRole(auto_prefetch.Model):
    """
    A Role of a Creator in a Game
    """

    game = auto_prefetch.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="gameroles"
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
        return f"{self.game} - {self.creator} - {self.role}"


class GameCast(auto_prefetch.Model):
    """
    A Cast in a Game
    """

    game = auto_prefetch.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="gamecasts"
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
        return f"{self.game} - {self.creator} - {self.role}"


class PlayCheckIn(auto_prefetch.Model):
    content_type = auto_prefetch.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    # game = auto_prefetch.ForeignKey(Game, on_delete=models.CASCADE)
    user = auto_prefetch.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    STATUS_CHOICES = [
        ("to_play", "To Play"),
        ("playing", "Playing"),
        ("played", "Played"),
        ("paused", "Paused"),
        ("abandoned", "Abandoned"),
        ("replaying", "Replaying"),
        ("replayed", "Replayed"),
        ("afterthoughts", "Afterthoughts"),
    ]
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
    share_to_feed = models.BooleanField(default=False)
    content = models.TextField(
        null=True, blank=True
    )  # Any thoughts or comments at this check-in.
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    progress = models.IntegerField(null=True, blank=True)
    TOTAL_PLAYED_TIME = "TT"
    PROGRESS_TYPE_CHOICES = [
        (TOTAL_PLAYED_TIME, "Played Time"),
    ]
    progress_type = models.CharField(
        max_length=2,
        choices=PROGRESS_TYPE_CHOICES,
        default=TOTAL_PLAYED_TIME,
    )
    comments = GenericRelation("write.Comment")
    comments_enabled = models.BooleanField(default=True)
    tags = models.ManyToManyField("write.Tag", blank=True)
    reposts = GenericRelation("write.Repost")
    votes = GenericRelation("discover.Vote")

    def get_absolute_url(self):
        return reverse(
            "write:play_checkin_detail",
            kwargs={"pk": self.pk, "username": self.user.username},
        )

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="playcheckin", object_id=self.id
            )
            return activity.id
        except ObjectDoesNotExist:
            return None

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0

    def model_name(self):
        return "Play Check-In"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        was_updated = False
        super().save(*args, **kwargs)
        # Attempt to fetch an existing Activity object for this check-in
        try:
            activity = Activity.objects.get(
                content_type__model="playcheckin", object_id=self.id
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
                        content_type__model="playcheckin", object_id=self.id
                    )
                    activity.save()  # This will trigger the update logic in Activity model
                except Activity.DoesNotExist:
                    pass  # Handle the case where the Activity object does not exist

            if is_new or activity is None:
                Activity.objects.create(
                    user=self.user,
                    activity_type="play-check-in",
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
                            "PlayCheckIn",
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
                            "PlayCheckIn",
                        )
                    except Exception as e:
                        print(f"Error creating Mastodon post: {e}")

        elif activity is not None:
            # Optionally, remove the Activity if share_to_feed is False
            activity.delete()
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


class GameSeries(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # data
    title = models.CharField(max_length=100)
    other_titles = models.TextField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)
    games = models.ManyToManyField(Game, through="GameInSeries", related_name="series")
    description = models.TextField(null=True, blank=True)

    # meta
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="series_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="series_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("play:series_detail", args=[str(self.id)])


class GameInSeries(auto_prefetch.Model):
    game = auto_prefetch.ForeignKey(Game, on_delete=models.CASCADE)
    series = auto_prefetch.ForeignKey(GameSeries, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["order"]

    def __str__(self):
        return f"{self.series.title}: {self.game.title}"


class DLC(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # dlc meta data
    game = auto_prefetch.ForeignKey(Game, on_delete=models.CASCADE, related_name="dlc")
    title = models.CharField(max_length=255, blank=True, null=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    other_titles = models.TextField(blank=True, null=True)
    release_date = models.CharField(max_length=10, blank=True, null=True)
    creators = models.ManyToManyField(
        Creator, through="DLCRole", related_name="dlc_role"
    )
    casts = models.ManyToManyField(Creator, through="DLCCast", related_name="dlc_cast")
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.title}"

    def get_absolute_url(self):
        return reverse("play:dlc_detail", args=[str(self.game.id), str(self.id)])


class DLCRole(auto_prefetch.Model):
    """
    A Role of a Creator in a DLC
    """

    dlc = auto_prefetch.ForeignKey(
        DLC, on_delete=models.CASCADE, related_name="dlcroles"
    )
    creator = auto_prefetch.ForeignKey(
        Creator, on_delete=models.CASCADE, null=True, blank=True
    )
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )
    alt_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.dlc} - {self.creator} - {self.role}"


class DLCCast(auto_prefetch.Model):
    """
    A Cast in a LDC
    """

    dlc = auto_prefetch.ForeignKey(
        DLC, on_delete=models.CASCADE, related_name="dlccasts"
    )
    creator = auto_prefetch.ForeignKey(
        Creator, on_delete=models.CASCADE, null=True, blank=True
    )
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )
    character_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.dlc} - {self.creator} - {self.role}"
