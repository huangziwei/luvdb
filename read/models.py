import os
import re
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
    if filename is None:
        filename = "default.jpg"
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


class ISBNField(models.CharField):
    def to_python(self, value):
        value = super().to_python(value)  # Call CharField's to_python method.
        if value is not None:
            value = value.replace("-", "")  # Remove hyphens.
        return value

    def validate(self, value, model_instance):
        super().validate(value, model_instance)  # Call CharField's validate method.
        if len(value) != 10 and len(value) != 13:  # Check ISBN length.
            raise ValidationError(
                f"Invalid ISBN length: {len(value)}. An ISBN should be either 10 or 13 characters long."
            )


def standardize_date(date_str):
    """
    Standardize date strings to be in the format YYYY.MM, YYYY.MM.DD, or YYYY depending on input.
    Can also accommodate BCE dates like "500 BCE" or "500 BCE.MM.DD".
    """
    # Replace common separators with a dot
    standardized_date = re.sub(r"[-/]", ".", date_str)

    # Handle BCE dates
    bce_match = re.match(
        r"(?P<year>\d{1,5}) BCE(\.(?P<month>\d{1,2})(\.(?P<day>\d{1,2}))?)?$",
        standardized_date,
    )
    if bce_match:
        year = bce_match.group("year")
        month = bce_match.group("month") or ""
        day = bce_match.group("day") or ""
        return f"-{year}.{month}.{day}".rstrip(".")  # Negative year denotes BCE

    # Handle CE dates
    if re.match(r"^\d{4}(\.\d{1,2}(\.\d{1,2})?)?$", standardized_date):
        return standardized_date

    # If not in a valid format, return the original string (or raise an error, based on your requirements)
    return date_str


# models


class Publisher(Entity):
    """
    A Publisher entity
    """

    # publisher meta data
    history = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)
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
                "zh-Hans",
                "zh-Hant",
            ]
            return language[0] not in POPULAR_LANGUAGES

        # Move popular languages to the top
        ALL_LANGUAGES.sort(key=popular_languages_first)

        return ALL_LANGUAGES


class Genre(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Work(models.Model):  # Renamed from Book
    """
    A Work entity
    """

    # work meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    persons = models.ManyToManyField(
        Person, through="WorkRole", related_name="read_works"
    )
    publication_date = models.TextField(blank=True, null=True)
    language = LanguageField(max_length=8, blank=True, null=True)

    # novel, novella, short story, poem, etc.
    WORK_TYPES = (
        ("NO", "Novel"),
        ("NV", "Novella"),
        ("SS", "Short Story"),
        ("PM", "Poem"),
        ("PL", "Play"),
        ("SC", "Screenplay"),
        ("NF", "Nonfiction"),
        ("OT", "Other"),
    )
    work_type = models.CharField(
        max_length=255, choices=WORK_TYPES, blank=True, null=True
    )  # novel, etc.
    genres = models.ManyToManyField(Genre, related_name="read_works", blank=True)
    wikipedia = models.URLField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

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

    def get_absolute_url(self):
        return reverse("read:work_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        # Convert the publication_date to a standard format if it's not None or empty
        if self.publication_date:
            self.publication_date = standardize_date(self.publication_date)
        super(Work, self).save(*args, **kwargs)


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
        related_name="read_workrole_set",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="read_workrole_set",
    )
    alt_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.work} - {self.person} - {self.role}"


class Instance(models.Model):
    """
    An Instance is a manifestation of a Work,
    that is, a specific edition, a translation, an installment of a serialization, etc.
    """

    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    persons = models.ManyToManyField(
        Person, through="InstanceRole", related_name="instances"
    )
    work = models.ForeignKey(
        Work, on_delete=models.SET_NULL, null=True, blank=True, related_name="instances"
    )
    publication_date = models.TextField(blank=True, null=True)
    language = LanguageField(max_length=8, blank=True, null=True)
    edition = models.CharField(
        max_length=255, blank=True, null=True
    )  # 1st ed., revised ed., etc.
    wikipedia = models.URLField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="instances_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="instances_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("read:instance_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        # Convert the publication_date to a standard format if it's not None or empty
        if self.publication_date:
            self.publication_date = standardize_date(self.publication_date)
        super(Instance, self).save(*args, **kwargs)


class InstanceRole(models.Model):
    instance = models.ForeignKey(Instance, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    alt_name = models.CharField(max_length=255, blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.instance} - {self.person} - {self.role}"


class Book(models.Model):
    """
    A Book entity of an Instance
    """

    # book meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    cover = models.ImageField(upload_to=rename_book_cover, null=True, blank=True)
    cover_sens = models.BooleanField(default=False, null=True, blank=True)
    persons = models.ManyToManyField(Person, through="BookRole", related_name="books")
    instances = models.ManyToManyField(
        Instance, through="BookInstance", related_name="books"
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        related_name="books",
        null=True,
        blank=True,
    )
    language = LanguageField(max_length=8, blank=True, null=True)
    publication_date = models.TextField(blank=True, null=True)
    wikipedia = models.URLField(max_length=200, blank=True, null=True)
    details = models.TextField(blank=True, null=True)

    # novel, novella, short story, poem, etc.
    format = models.CharField(
        max_length=255, blank=True, null=True
    )  # hardcover, paperback, etc.
    length = models.CharField(
        max_length=255, blank=True, null=True
    )  # e.g. 300 pages, 10:00:00, etc.
    price = models.CharField(
        max_length=20, blank=True, null=True
    )  # e.g. 1,000 JPY, $10.00 USD, etc.
    isbn_10 = ISBNField(
        max_length=20,
        blank=True,
        null=True,
    )
    isbn_13 = ISBNField(
        max_length=20,
        blank=True,
        null=True,
    )
    eisbn_13 = ISBNField(
        max_length=20,
        blank=True,
        null=True,
    )
    asin = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        validators=[validate_asin],
    )
    internet_archive_url = models.URLField(max_length=200, blank=True, null=True)
    readcheckin = GenericRelation("ReadCheckIn")

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

    @property
    def checkin_count(self):
        return (
            self.readcheckin_set.count()
        )  # adjust this if your related name is different

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

                # remove the original image
                self.cover.delete(save=False)

                # Save the BytesIO object to the FileField
                self.cover.save(
                    self.cover.name, ContentFile(temp_file.read()), save=False
                )

            img.close()

        # Convert the publication_date to a standard format if it's not None or empty
        if self.publication_date:
            self.publication_date = standardize_date(self.publication_date)

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


class BookInstance(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    instance = models.ForeignKey(
        Instance, on_delete=models.CASCADE, null=True, blank=True
    )
    order = models.PositiveIntegerField(
        null=True, blank=True, default=1
    )  # Ordering of the works in a book

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.book} - {self.instance} - {self.order}"


# This receiver handles deletion of the cover file when the Book instance is deleted
@receiver(signals.post_delete, sender=Book)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `Book` object is deleted.
    """
    if instance.cover:
        instance.cover.delete(save=False)


class ReadCheckIn(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    STATUS_CHOICES = [
        ("to_read", "To Read"),
        ("reading", "Reading"),
        ("finished_reading", "Read"),
        ("paused", "Paused"),
        ("abandoned", "Abandoned"),
        ("rereading", "Rereading"),
        ("reread", "Reread"),
        ("afterthoughts", "Afterthoughts"),
    ]
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
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
        return reverse("read:read_checkin_detail", args=[str(self.id)])

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="readcheckin", object_id=self.id
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
                activity_type="read-check-in",
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
    wikipedia = models.URLField(max_length=200, blank=True, null=True)
    website = models.URLField(max_length=200, blank=True, null=True)

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="periodicals_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="periodicals_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title


class Issue(models.Model):
    periodical = models.ForeignKey(
        Periodical, on_delete=models.CASCADE, related_name="issues"
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        related_name="published_issues",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    volume = models.IntegerField(blank=True, null=True)
    number = models.IntegerField(blank=True, null=True)
    publication_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    cover = models.ImageField(upload_to=rename_book_cover, null=True, blank=True)
    internet_archive_url = models.URLField(max_length=200, blank=True, null=True)

    instances = models.ManyToManyField(
        Instance, through="IssueInstance", related_name="issues"
    )

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="issues_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="issues_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    readcheckin = GenericRelation("ReadCheckIn")

    def __str__(self):
        return f"{self.periodical.title} - Issue {self.number} - Volume {self.volume}"

    def get_absolute_url(self):
        return reverse(
            "read:issue_detail", args=[str(self.periodical.id), str(self.id)]
        )

    @property
    def checkin_count(self):
        return (
            self.readcheckin_set.count()
        )  # adjust this if your related name is different


class IssueInstance(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
    instance = models.ForeignKey(
        Instance, on_delete=models.CASCADE, null=True, blank=True
    )
    order = models.PositiveIntegerField(
        null=True, blank=True, default=1
    )  # Ordering of the works in a book

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.issue} - {self.instance} - {self.order}"


class BookSeries(models.Model):
    title = models.CharField(max_length=100)
    books = models.ManyToManyField(Book, through="BookInSeries", related_name="series")
    description = models.TextField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="bookseries_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="bookseries_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("read:series_detail", args=[str(self.id)])


class BookInSeries(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    series = models.ForeignKey(BookSeries, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.series.title}: {self.book.title}"
