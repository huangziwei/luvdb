import os
import uuid
from io import BytesIO

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
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
def rename_game_cover(instance, filename):
    if filename is None:
        filename = "default.jpg"
    _, extension = os.path.splitext(filename)
    unique_id = uuid.uuid4()
    directory_name = (
        f"{slugify(instance.title, allow_unicode=True)}-{instance.release_date}"
    )
    new_name = f"{unique_id}{extension}"
    return os.path.join("covers", directory_name, new_name)


# Create your models here.
class Developer(Entity):
    history = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    founded_date = models.DateField(blank=True, null=True)
    closed_date = models.DateField(blank=True, null=True)

    def __str__(self):
        if self.location:
            return f"{self.location}: {self.name}"
        return self.name


class GamePublisher(Entity):
    history = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    founded_date = models.DateField(blank=True, null=True)
    closed_date = models.DateField(blank=True, null=True)

    def __str__(self):
        if self.location:
            return f"{self.location}: {self.name}"
        return self.name


class Platform(Entity):
    history = models.TextField(blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    release_date = models.CharField(max_length=10, blank=True, null=True)
    discontinued_date = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.name


class Work(models.Model):  # Renamed from Book
    """
    A Work entity
    """

    # work meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    romanized_title = models.CharField(max_length=100, blank=True, null=True)
    persons = models.ManyToManyField(
        Person, through="WorkRole", related_name="play_works"
    )
    developers = models.ManyToManyField(Developer, related_name="play_works")

    first_release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD

    # novel, novella, short story, poem, etc.
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
    )  # novel, etc.

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="play_works_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="play_works_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title


class WorkRole(models.Model):  # Renamed from BookRole
    """
    A Role of a Person in a Work
    """

    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="play_workrole_set",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="play_workrole_set",
    )
    alt_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.work} - {self.person} - {self.role}"


class Game(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, blank=True, null=True)
    romanized_title = models.CharField(max_length=100, blank=True, null=True)
    work = models.ForeignKey(
        Work, on_delete=models.CASCADE, null=True, blank=True, related_name="games"
    )

    developers = models.ManyToManyField(Developer, related_name="games")
    publishers = models.ManyToManyField(GamePublisher, related_name="games")

    persons = models.ManyToManyField(Person, through="GameRole", related_name="games")
    casts = models.ManyToManyField(
        Person, through="GameCast", related_name="games_cast"
    )
    release_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    description = models.TextField(blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    cover = models.ImageField(upload_to=rename_game_cover, null=True, blank=True)
    cover_sens = models.BooleanField(default=False, null=True, blank=True)
    price = models.CharField(max_length=20, blank=True, null=True)
    platforms = models.ManyToManyField(Platform, related_name="games")

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="games_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="games_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Game.objects.get(pk=self.pk)
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
            self.cover.close()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("play:game_detail", args=[str(self.id)])


class GameRole(models.Model):
    """
    A Role of a Person in a Game
    """

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="gameroles")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    alt_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.game} - {self.person} - {self.role}"


class GameCast(models.Model):
    """
    A Cast in a Game
    """

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="gamecasts")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    character_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.game} - {self.person} - {self.role}"


class GameCheckIn(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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

    def get_absolute_url(self):
        return reverse("play:game_checkin_detail", args=[str(self.id)])

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="gamecheckin", object_id=self.id
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
                activity_type="game-check-in",
                content_object=self,
            )
        else:
            print("Not creating activity")
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


class GameSeries(models.Model):
    # data
    title = models.CharField(max_length=100)
    games = models.ManyToManyField(Game, through="GameInSeries", related_name="series")

    # meta
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="series_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="series_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("play:series_detail", args=[str(self.id)])


class GameInSeries(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    series = models.ForeignKey(GameSeries, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.series.title}: {self.game.title}"
