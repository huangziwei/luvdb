import auto_prefetch
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from simple_history.models import HistoricalRecords

from activity_feed.models import Activity
from write.models import create_mentions_notifications, handle_tags
from write.utils_bluesky import create_bluesky_post
from write.utils_mastodon import create_mastodon_post


def get_location_full_name(location):
    """
    Generate the full name of a location by traversing its parent hierarchy.
    """
    names = []
    current = location
    while current:
        current_name = current.name
        if current.historical:
            if current.historical_period:
                current_name += f" ({current.historical_period})"
            else:
                current_name += " (historical)"
        names.insert(0, current_name)
        current = current.parent
    # name = " / ".join(names)
    return names


class Location(models.Model):
    locked = models.BooleanField(default=False)

    LEVEL0 = "level0"
    LEVEL1 = "level1"
    LEVEL2 = "level2"
    LEVEL3 = "level3"
    LEVEL4 = "level4"
    LEVEL5 = "level5"
    LEVEL6 = "level6"
    LEVEL7 = "level7"

    LOCATION_LEVELS = [
        (LEVEL0, "Level 0"),
        (LEVEL1, "Level 1"),
        (LEVEL2, "Level 2"),
        (LEVEL3, "Level 3"),
        (LEVEL4, "Level 4"),
        (LEVEL5, "Level 5"),
        (LEVEL6, "Level 6"),
        (LEVEL7, "Level 7"),
    ]

    DEFAULT_LEVEL_NAMES = {
        LEVEL0: "Continent",
        LEVEL1: "Polity",
        LEVEL2: "State / Province / Region / Prefecture / Canton",
        LEVEL3: "County / Prefecture-level City",
        LEVEL4: "Town / Township / Village / County-level City",
        LEVEL5: "District / Borough / Ward / Neighborhood",
        LEVEL6: "Point of Interest",
        LEVEL7: "Others",
    }

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    other_names = models.TextField(null=True, blank=True)
    level = models.CharField(max_length=20, choices=LOCATION_LEVELS)
    level_name = models.CharField(
        max_length=255, null=True, blank=True
    )  # User-defined or default label for the level
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    historical = models.BooleanField(default=False)
    historical_period = models.CharField(max_length=255, null=True, blank=True)
    current_identity = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="historical_identity",
    )

    osm_id = models.CharField(max_length=255, null=True, blank=True)
    OSM_ID_TYPES = [
        ("node", "Node"),
        ("way", "Way"),
        ("relation", "Relation"),
    ]
    osm_id_type = models.CharField(
        max_length=20, choices=OSM_ID_TYPES, null=True, blank=True, default="relation"
    )
    address = models.TextField(null=True, blank=True)  # for POI

    wikipedia = models.URLField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    # Entry meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="locations_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="locations_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)
    votes = GenericRelation("discover.Vote")

    def __str__(self):
        return " / ".join(get_location_full_name(self))

    def save(self, *args, **kwargs):
        if not self.level_name:
            self.level_name = self.DEFAULT_LEVEL_NAMES.get(self.level)
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("visit:location_detail", kwargs={"pk": self.pk})

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0

    # @property
    # def full_name_on_feed(self):
    #     names = get_location_full_name(self)[:-1][::-1]
    #     if len(names) > 0:
    #         return " < ".join(names)
    #     else:
    #         return ""


class VisitCheckIn(auto_prefetch.Model):
    content_type = auto_prefetch.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    # game = auto_prefetch.ForeignKey(Game, on_delete=models.CASCADE)
    user = auto_prefetch.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    STATUS_CHOICES = [
        ("to_visit", "To visit"),
        ("visiting", "Visiting"),
        ("visited", "Visited"),
        ("revisiting", "Revisiting"),
        ("revisited", "Revisited"),
        ("living-here", "Live here"),
        ("lived-there", "Lived there"),
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
    STAYED_TIME = "ST"
    PROGRESS_TYPE_CHOICES = [
        (STAYED_TIME, "Stayed Time"),
    ]
    progress_type = models.CharField(
        max_length=2,
        choices=PROGRESS_TYPE_CHOICES,
        default=STAYED_TIME,
    )
    comments = GenericRelation("write.Comment")
    comments_enabled = models.BooleanField(default=True)
    tags = models.ManyToManyField("write.Tag", blank=True)
    reposts = GenericRelation("write.Repost")
    votes = GenericRelation("discover.Vote")

    def get_absolute_url(self):
        return reverse(
            "write:visit_checkin_detail",
            kwargs={"pk": self.pk, "username": self.user.username},
        )

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="visitcheckin", object_id=self.id
            )
            return activity.id
        except ObjectDoesNotExist:
            return None

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0

    def model_name(self):
        return "Visit Check-In"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        was_updated = False
        super().save(*args, **kwargs)
        # Attempt to fetch an existing Activity object for this check-in
        try:
            activity = Activity.objects.get(
                content_type__model="visitcheckin", object_id=self.id
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
                        content_type__model="visitcheckin", object_id=self.id
                    )
                    activity.save()  # This will trigger the update logic in Activity model
                except Activity.DoesNotExist:
                    pass  # Handle the case where the Activity object does not exist

            if is_new or activity is None:
                Activity.objects.create(
                    user=self.user,
                    activity_type="visit-check-in",
                    content_object=self,
                )

                if hasattr(self.user, "bluesky_account"):
                    try:
                        bluesky_account = self.user.bluesky_account
                        create_bluesky_post(
                            bluesky_account.bluesky_handle,
                            bluesky_account.bluesky_pds_url,
                            bluesky_account.get_bluesky_app_password(),  # Ensure this method securely retrieves the password
                            f'I checked in to "{self.content_object.name}" on LʌvDB\n\n'
                            + self.content
                            + "\n\n",
                            self.id,
                            self.user.username,
                            "VisitCheckIn",
                        )
                    except Exception as e:
                        print(f"Error creating Bluesky post: {e}")

                if hasattr(self.user, "mastodon_account"):
                    try:
                        mastodon_account = self.user.mastodon_account
                        create_mastodon_post(
                            mastodon_account.mastodon_handle,
                            mastodon_account.get_mastodon_access_token(),  # Ensure this method securely retrieves the password
                            f'I checked in to "{self.content_object.name}" on LʌvDB\n\n'
                            + self.content
                            + "\n\n",
                            self.id,
                            self.user.username,
                            "VisitCheckIn",
                        )
                    except Exception as e:
                        print(f"Error creating Mastodon post: {e}")

        elif activity is not None:
            # Optionally, remove the Activity if share_to_feed is False
            activity.delete()
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)
