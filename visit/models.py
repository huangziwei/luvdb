import auto_prefetch
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from simple_history.models import HistoricalRecords


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
    name = " / ".join(names)
    return name


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

    def __str__(self):
        return get_location_full_name(self)

    def save(self, *args, **kwargs):
        if not self.level_name:
            self.level_name = self.DEFAULT_LEVEL_NAMES.get(self.level)
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)
