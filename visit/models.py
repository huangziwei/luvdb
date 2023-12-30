import auto_prefetch
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from simple_history.models import HistoricalRecords


class Location(models.Model):
    locked = models.BooleanField(default=False)

    CONTINENT = "continent"
    POLITY = "polity"  # countries /  sovereign entities
    REGION = "region"  # State / Province
    CITY = "city"  # city / town / village can be or not be at the same level
    TOWN = "town"
    VILLAGE = "village"
    DISTRICT = "district"  # Neighborhood / District
    POI = "poi"  # Point of Interest

    LOCATION_LEVELS = [
        (CONTINENT, "Continent"),
        (POLITY, "Polity"),
        (REGION, "Region"),
        (CITY, "City"),
        (TOWN, "Town"),
        (VILLAGE, "Village"),
        (DISTRICT, "District"),
        (POI, "Point of Interest"),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    other_names = models.TextField(null=True, blank=True)
    level = models.CharField(max_length=20, choices=LOCATION_LEVELS)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    historical = models.BooleanField(default=False)
    historical_period = models.CharField(max_length=255, null=True, blank=True)

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
        if self.level == "continent":
            return f"{self.name}"
        elif self.level == "polity":
            return f"{self.parent.name} / {self.name}"
        elif self.level == "region":
            return f"{self.parent.parent.name} / {self.parent.name} / {self.name}"
        elif self.level == "city":
            if self.parent.level == "region":
                return f"{self.parent.parent.parent.name} / {self.parent.parent.name} / {self.parent.name} / {self.name}"
            elif self.parent.level == "polity":
                return f"{self.parent.parent.name} / {self.parent.name} / {self.name}"
            else:
                return f"{self.parent.name} / {self.name}"
        elif self.level == "district":
            return f"{self.parent.parent.parent.parent.name} / {self.parent.parent.parent.name} / {self.parent.parent.name} / {self.parent.name} / {self.name}"
        elif self.level == "poi":
            return f"{self.parent.parent.parent.parent.parent.name} / {self.parent.parent.parent.parent.name} / {self.parent.parent.parent.name} / {self.parent.parent.name} / {self.parent.name} / {self.name}"
        else:
            return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)
