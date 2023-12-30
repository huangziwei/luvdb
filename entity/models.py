import auto_prefetch
import pycountry
from django.conf import settings
from django.db import models
from django.urls import reverse
from langcodes import Language
from simple_history.models import HistoricalRecords

from visit.models import Location


class LanguageField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 8
        kwargs["blank"] = True
        kwargs["null"] = True
        kwargs["default"] = None
        kwargs["choices"] = self.get_language_choices()
        super(LanguageField, self).__init__(*args, **kwargs)

    def get_language_choices(self):
        ALL_LANGUAGES = [
            (lang.alpha_2, f"{Language.make(lang.alpha_2).autonym()} ({lang.alpha_2})")
            for lang in pycountry.languages
            if hasattr(lang, "alpha_2")
        ]

        # Add Simplified and Traditional Chinese
        ALL_LANGUAGES.extend(
            [
                ("zh-Hans", f"{Language.make('zh-Hans').autonym()} (zh-Hans)"),
                ("zh-Hant", f"{Language.make('zh-Hant').autonym()} (zh-Hant)"),
            ]
        )

        # Sort languages by their English name
        ALL_LANGUAGES.sort(key=lambda x: x[1])

        def popular_languages_first(language):
            POPULAR_LANGUAGES = [
                "en",
                "es",
                "fr",
                "de",
                "ja",
                "ru",
                "zh-Hans",
                "zh-Hant",
            ]
            return language[0] not in POPULAR_LANGUAGES

        # Move popular languages to the top
        ALL_LANGUAGES.sort(key=popular_languages_first)

        return ALL_LANGUAGES


# Create your models here.
class Entity(auto_prefetch.Model):
    """
    An Entity base model
    """

    # admin
    locked = models.BooleanField(default=False)

    # entity meta data
    name = models.CharField(max_length=255)
    # romanized_name = models.CharField(max_length=255, blank=True, null=True)
    other_names = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="%(class)s_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="%(class)s_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    history = HistoricalRecords(inherit=True)

    class Meta(auto_prefetch.Model.Meta):
        abstract = True

    def __str__(self):
        return self.name


class Creator(Entity):
    """
    A Creator entity
    ---
    // Renamed from Person
    """

    CREATOR_TYPES = (
        ("person", "Person"),
        ("group", "Group"),
    )

    creator_type = models.CharField(
        max_length=10, choices=CREATOR_TYPES, default="person", blank=True, null=True
    )

    # person meta data
    birth_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    death_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    birth_place = models.CharField(max_length=255, blank=True, null=True)
    death_place = models.CharField(max_length=255, blank=True, null=True)
    birth_location = auto_prefetch.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="birth_location",
    )
    death_location = auto_prefetch.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="death_location",
    )
    wikipedia = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("entity:creator_detail", kwargs={"pk": self.pk})


class Role(auto_prefetch.Model):
    DOMAIN_CHOICES = (
        ("read", "Read"),
        ("listen", "Listen"),
        ("watch", "Watch"),
        ("play", "Play"),
        # Add more domains as needed
    )

    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=20, choices=DOMAIN_CHOICES)

    class Meta(auto_prefetch.Model.Meta):
        unique_together = ("name", "domain")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = " ".join([word.capitalize() for word in self.name.split()])
        return super(Role, self).save(*args, **kwargs)


class Company(Entity):
    location = models.CharField(max_length=100, blank=True, null=True)
    location_new = auto_prefetch.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="location",
    )
    founded_date = models.CharField(max_length=10, blank=True, null=True)
    defunct_date = models.CharField(max_length=10, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        if self.location:
            return f"{self.location}: {self.name}"
        return self.name
