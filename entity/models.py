import auto_prefetch
import pycountry
from django.conf import settings
from django.db import models
from django.urls import reverse
from langcodes import Language
from simple_history.models import HistoricalRecords

from visit.models import Location
from visit.utils import get_location_hierarchy_ids


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
    # group meta data
    active_years = models.CharField(max_length=255, blank=True, null=True)
    origin_location = auto_prefetch.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="origin_location",
    )

    birth_location_hierarchy = models.TextField(blank=True, null=True)
    death_location_hierarchy = models.TextField(blank=True, null=True)
    origin_location_hierarchy = models.TextField(blank=True, null=True)

    wikipedia = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("entity:creator_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if self.birth_location:
            self.birth_location_hierarchy = ",".join(
                get_location_hierarchy_ids(self.birth_location)
            )
        if self.death_location:
            self.death_location_hierarchy = ",".join(
                get_location_hierarchy_ids(self.death_location)
            )
        if self.origin_location:
            self.origin_location_hierarchy = ",".join(
                get_location_hierarchy_ids(self.origin_location)
            )
        super().save(*args, **kwargs)


class MemberOf(auto_prefetch.Model):
    """
    Member Of
    """

    creator = auto_prefetch.ForeignKey(
        Creator, on_delete=models.CASCADE, related_name="member_of"
    )
    group = auto_prefetch.ForeignKey(
        Creator,
        on_delete=models.CASCADE,
        related_name="members",
        null=True,
        blank=True,
    )
    notes = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.CharField(max_length=10, blank=True, null=True)
    end_date = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.creator} < {self.group}"


class Role(auto_prefetch.Model):
    DOMAIN_CHOICES = (
        ("read", "Read"),
        ("listen", "Listen"),
        ("watch", "Watch"),
        ("play", "Play"),
        # Add more domains as needed
    )

    CATEGORIES = (
        ("Performing Artists", "Performing Artists"),
        ("Composition and Lyrics", "Composition and Lyrics"),
        ("Production and Engineering", "Production and Engineering"),
    )

    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=20, choices=DOMAIN_CHOICES)
    category = models.CharField(
        max_length=255, choices=CATEGORIES, blank=True, null=True
    )

    class Meta(auto_prefetch.Model.Meta):
        unique_together = ("name", "domain", "category")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = " ".join([word.capitalize() for word in self.name.split()])
        return super(Role, self).save(*args, **kwargs)


class Company(Entity):
    location = auto_prefetch.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="location",
    )
    location_hierarchy = models.TextField(blank=True, null=True)
    founded_date = models.CharField(max_length=10, blank=True, null=True)
    defunct_date = models.CharField(max_length=10, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        if self.location:
            return f"{self.location.name}: {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if self.location:
            self.location_hierarchy = ",".join(
                get_location_hierarchy_ids(self.location)
            )
        super().save(*args, **kwargs)


class CompanyParent(auto_prefetch.Model):
    """
    Parent Company
    """

    child = auto_prefetch.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="parent_companies"
    )
    parent = auto_prefetch.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="child_companies",
        null=True,
        blank=True,
    )
    alt_name = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.CharField(max_length=10, blank=True, null=True)
    end_date = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.child} < {self.alt_name}"


class CompanyPastName(auto_prefetch.Model):
    """
    Past Name
    """

    company = auto_prefetch.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="past_names"
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.CharField(max_length=10, blank=True, null=True)
    end_date = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.company} < {self.name}"
