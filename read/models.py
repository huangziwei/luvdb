import os
import uuid
from io import BytesIO

import pycountry
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from django.urls import reverse
from django.utils.text import slugify
from langcodes import Language
from PIL import Image

from activity_feed.models import Activity
from entity.models import Entity, Person, Role
from write.models import create_mentions_notifications, handle_tags


# helpers
def rename_book_cover(instance, filename):
    _, extension = os.path.splitext(filename)
    unique_id = uuid.uuid4()
    directory_name = (
        f"{slugify(instance.title, allow_unicode=True)}-{instance.publication_date}"
    )
    new_name = f"{unique_id}{extension}"
    return os.path.join("covers", directory_name, new_name)


# validators
def validate_isbn_10(value):
    if len(value) != 10:
        raise ValidationError("This field requires exactly 10 characters.")


def validate_isbn_13(value):
    if len(value) != 13:
        raise ValidationError("This field requires exactly 13 characters.")


def validate_asin(value):
    if len(value) != 10:
        raise ValidationError("This field requires exactly 10 characters.")


# models


class Publisher(Entity):
    """
    A Publisher entity
    """

    # publisher meta data
    history = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    founded_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    closed_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD

    def __str__(self):
        if self.location:
            return f"{self.location}: {self.name}"
        return self.name


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
                "ar",
                "zh-Hans",
                "zh-Hant",
            ]
            return language[0] not in POPULAR_LANGUAGES

        # Move popular languages to the top
        ALL_LANGUAGES.sort(key=popular_languages_first)

        return ALL_LANGUAGES


class Work(models.Model):  # Renamed from Book
    """
    A Work entity
    """

    # work meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    persons = models.ManyToManyField(Person, through="WorkRole", related_name="works")
    publication_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD

    language = LanguageField(max_length=8, blank=True, null=True)

    # novel, novella, short story, poem, etc.
    WORK_TYPES = (
        ("NO", "Novel"),
        ("NV", "Novella"),
        ("SS", "Short Story"),
        ("PO", "Poem"),
        ("ES", "Essay"),
        ("OT", "Other"),
    )
    work_type = models.CharField(
        max_length=255, choices=WORK_TYPES, blank=True, null=True
    )  # novel, etc.

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="works_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="works_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # check if object is new or not
        super().save(*args, **kwargs)
        if is_new:  # if new object has been created
            edition = Edition.objects.create(
                title=self.title,
                subtitle=self.subtitle,
                publication_date=self.publication_date,
                language=self.language,
                work=self,
            )
            # Create corresponding EditionRole instances
            for work_role in self.workrole_set.all():
                print(work_role)
                EditionRole.objects.create(
                    edition=edition,
                    person=work_role.person,
                    role=work_role.role,
                    alt_name=None,  # Replace with actual value if necessary
                )


class WorkRole(models.Model):  # Renamed from BookRole
    """
    A Role of a Person in a Work
    """

    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.work} - {self.person} - {self.role}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # check if object is new or not
        super().save(*args, **kwargs)
        if is_new:  # if new object has been created
            # Check if there is an Edition associated with this Work
            edition = self.work.editions.first()
            if edition is not None:
                EditionRole.objects.create(
                    edition=edition,
                    person=self.person,
                    role=self.role,
                    alt_name=None,  # Replace with actual value if necessary
                )


class Edition(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    persons = models.ManyToManyField(
        Person, through="EditionRole", related_name="editions"
    )
    work = models.ForeignKey(
        Work, on_delete=models.SET_NULL, null=True, blank=True, related_name="editions"
    )
    publication_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    language = LanguageField(max_length=8, blank=True, null=True)

    def __str__(self):
        return self.title


class EditionRole(models.Model):
    edition = models.ForeignKey(Edition, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    alt_name = models.CharField(max_length=255, blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.edition} - {self.person} - {self.role}"


class Book(models.Model):
    """
    A Book entity of an Edition
    """

    # book meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    cover = models.ImageField(upload_to=rename_book_cover, null=True, blank=True)
    cover_sens = models.BooleanField(default=False)
    persons = models.ManyToManyField(Person, through="BookRole", related_name="books")
    editions = models.ManyToManyField(
        Edition, through="BookEdition", related_name="books"
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        related_name="books",
        null=True,
        blank=True,
    )
    language = LanguageField(max_length=8, blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    publication_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    format = models.CharField(
        max_length=255, blank=True, null=True
    )  # hardcover, paperback, etc.
    pages = models.IntegerField(blank=True, null=True)
    price = models.CharField(max_length=20, blank=True, null=True)
    isbn_10 = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        validators=[validate_isbn_10],
    )
    isbn_13 = models.CharField(
        max_length=13,
        blank=True,
        null=True,
        validators=[validate_isbn_13],
    )
    asin = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        validators=[validate_asin],
    )

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="books_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="books_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("read:book_detail", args=[str(self.id)])

    def save(self, *args, **kwargs):
        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Book.objects.get(pk=self.pk)
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

                # Save the BytesIO object to the FileField
                self.cover.save(
                    self.cover.name, ContentFile(temp_file.read()), save=False
                )

            img.close()
            self.cover.close()

        super().save(*args, **kwargs)


class BookRole(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_query_name="book_roles",
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    alt_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.book} - {self.alt_name or self.person.name} - {self.role}"


class BookEdition(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    edition = models.ForeignKey(
        Edition, on_delete=models.CASCADE, null=True, blank=True
    )
    order = models.PositiveIntegerField(
        null=True, blank=True, default=1
    )  # Ordering of the works in a book

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.book} - {self.edition} - {self.order}"


# This receiver handles deletion of the cover file when the Book instance is deleted
@receiver(signals.post_delete, sender=Book)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `Book` object is deleted.
    """
    if instance.cover:
        instance.cover.delete(save=False)


class BookCheckIn(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    READING_STATUS_CHOICES = [
        ("to_read", "To Read"),
        ("reading", "Reading"),
        ("finished_reading", "Read"),
        ("paused", "Paused"),
        ("abandoned", "Abandoned"),
        ("rereading", "Rereading"),
        ("reread", "Reread"),
    ]
    status = models.CharField(max_length=255, choices=READING_STATUS_CHOICES)
    share_to_feed = models.BooleanField(default=False)
    content = models.TextField(
        null=True, blank=True
    )  # Any thoughts or comments at this check-in.
    timestamp = models.DateTimeField(auto_now_add=True)
    progress = models.IntegerField(null=True, blank=True)
    PAGE = "PG"
    PERCENTAGE = "PC"
    PROGRESS_TYPE_CHOICES = [
        (PAGE, "Page"),
        (PERCENTAGE, "Percentage"),
    ]
    progress_type = models.CharField(
        max_length=2,
        choices=PROGRESS_TYPE_CHOICES,
        default=PAGE,
    )
    comments = GenericRelation("write.Comment")
    comments_enabled = models.BooleanField(default=True)
    tags = models.ManyToManyField("write.Tag", blank=True)
    reposts = GenericRelation("write.Repost")

    def get_absolute_url(self):
        return reverse("read:book_checkin_detail", args=[str(self.id)])

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="bookcheckin", object_id=self.id
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
                activity_type="book-check-in",
                content_object=self,
            )
        else:
            print("Not creating activity")
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


class Periodical(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        related_name="periodicals",
        null=True,
        blank=True,
    )
    FREQUENCY_CHOICES = (
        ("D", "Daily"),
        ("SW", "Semiweekly"),
        ("W", "Weekly"),
        ("BW", "Biweekly"),
        ("SM", "Semimonthly"),
        ("M", "Monthly"),
        ("SQ", "Semiquarterly"),
        ("BM", "Bimonthly"),
        ("Q", "Quarterly"),
        ("SA", "Semiannually"),
        ("A", "Annually"),
        ("B", "Biennially"),
        ("T", "Triennially"),
        ("Q", "Quadrennially"),
        ("QQ", "Quinquennially"),
        # Add more frequencies if needed
    )
    frequency = models.CharField(
        max_length=2, choices=FREQUENCY_CHOICES, blank=True, null=True
    )
    language = LanguageField(max_length=8, blank=True, null=True)
    issn = models.CharField(max_length=8, blank=True, null=True)
    website = models.URLField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.title


class Issue(models.Model):
    periodical = models.ForeignKey(
        Periodical, on_delete=models.CASCADE, related_name="issues"
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    volume = models.IntegerField(blank=True, null=True)
    number = models.IntegerField(blank=True, null=True)
    publication_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    cover = models.ImageField(upload_to=rename_book_cover, null=True, blank=True)
    editions = models.ManyToManyField(
        Edition, through="IssueEdition", related_name="issues"
    )

    def __str__(self):
        return f"{self.periodical.title} - Issue {self.number} - Volume {self.volume}"


class IssueEdition(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
    edition = models.ForeignKey(
        Edition, on_delete=models.CASCADE, null=True, blank=True
    )
    order = models.PositiveIntegerField(
        null=True, blank=True, default=1
    )  # Ordering of the works in a book

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.issue} - {self.edition} - {self.order}"
