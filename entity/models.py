import os
import uuid
from io import BytesIO

import auto_prefetch
import pycountry
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils.text import slugify
from langcodes import Language
from PIL import Image
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


def cover_upload_path(instance, filename):
    """
    Generates the upload path for additional cover images in CoverAlbum.
    Ensures that extra images are saved in the same folder as the primary cover.

    Books, Games, Releases → `covers/`
    Movies, Series → `posters/`
    """
    if not hasattr(instance, "cover_album") or not instance.cover_album:
        raise ValueError("CoverImage must be related to a CoverAlbum.")

    # Get the related object (Book, Movie, Game, Release)
    related_object = instance.cover_album.content_object

    # Determine base folder dynamically using content type
    content_type = instance.cover_album.content_type.model  # Lowercase model name
    base_folder = "posters" if content_type in ["movie", "series"] else "covers"

    # Use the same folder as the primary cover if it exists
    if related_object.cover:
        existing_cover_path = related_object.cover.name  # e.g., covers/負けヒロインが多すぎる-5-2023.03.17/9478d796-d6bc-459c-9f71-2d579d4196dd.webp
        cover_dir = os.path.dirname(existing_cover_path)  # Extracts 'covers/負けヒロインが多すぎる-5-2023.03.17'
    else:
        # If no cover exists, generate a folder based on title (slugified)
        cover_dir = f"{base_folder}/{slugify(related_object.title, allow_unicode=True)}"

    # Generate a new unique filename
    _, ext = os.path.splitext(filename)
    new_filename = f"{uuid.uuid4()}{ext}"

    return f"{cover_dir}/{new_filename}"


class CoverAlbum(models.Model):
    """
    Stores multiple images for Books, Movies, Games, Releases, etc.
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CoverAlbum for {self.content_object}"


class CoverImage(models.Model):
    """
    Stores individual images in a CoverAlbum.
    """
    cover_album = models.ForeignKey(CoverAlbum, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=cover_upload_path)
    is_primary = models.BooleanField(default=False)  # Main cover image

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """
        Automatically resize image and convert to WEBP.
        """
        if self.image:
            img = Image.open(self.image)
            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)

            temp_file = BytesIO()
            img.save(temp_file, format="WEBP")
            temp_file.seek(0)

            webp_name = os.path.splitext(self.image.name)[0] + ".webp"
            self.image.save(webp_name, ContentFile(temp_file.read()), save=False)

            img.close()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cover for {self.cover_album.content_object} - {self.image.name}"

# Automatically delete the image file when CoverImage is deleted
@receiver(post_delete, sender=CoverImage)
def delete_cover_image_file(sender, instance, **kwargs):
    if instance.image:
        storage = instance.image.storage  # Get storage backend
        storage.delete(instance.image.name)