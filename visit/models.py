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

    CONTINENT = "continent"
    POLITY = "polity"  # countries /  sovereign entities
    REGION = "region"  # State / Province
    CITY = "city"  # City / Municipality / Prefecture / County
    TOWN = "town"
    VILLAGE = "village"
    DISTRICT = "district"  # Neighborhood / District
    POI = "poi"  # Point of Interest

    LOCATION_LEVELS = [
        (CONTINENT, "Continent"),
        (POLITY, "Polity"),
        (REGION, "Region / State / Province / Canton / Prefecture"),
        (CITY, "City / Municipality / County"),
        (TOWN, "Town / Township"),
        (VILLAGE, "Village"),
        (DISTRICT, "District / Borough / Ward / Neighborhood"),
        (POI, "Point of Interest"),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    other_names = models.TextField(null=True, blank=True)
    level = models.CharField(max_length=20, choices=LOCATION_LEVELS)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    historical = models.BooleanField(default=False)
    historical_period = models.CharField(max_length=255, null=True, blank=True)
    current_identity = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="current"
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
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)
