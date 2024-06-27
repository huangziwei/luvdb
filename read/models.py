import os
import re
import uuid
from io import BytesIO

import auto_prefetch
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
from PIL import Image
from simple_history.models import HistoricalRecords

from activity_feed.models import Activity
from discover.utils import user_has_upvoted
from entity.models import Company, Creator, LanguageField, Role
from visit.models import Location
from visit.utils import get_location_hierarchy_ids
from write.models import (
    create_mentions_notifications,
    find_mentioned_users,
    handle_tags,
)


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


class Genre(auto_prefetch.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Work(auto_prefetch.Model):  # Renamed from Book
    """
    A Work entity
    """

    # admin
    locked = models.BooleanField(default=False)

    # work meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    creators = models.ManyToManyField(
        Creator, through="WorkRole", related_name="read_works"
    )
    publication_date = models.TextField(blank=True, null=True)
    language = LanguageField(max_length=8, blank=True, null=True)

    related_locations = models.ManyToManyField(
        Location, related_name="works_set_here", blank=True
    )
    related_locations_hierarchy = models.TextField(blank=True, null=True)

    # novel, novella, short story, poem, etc.
    WORK_TYPES = (
        # literature / fictions
        ("NO", "Novel"),
        ("NV", "Novella"),
        ("NT", "Novelette"),
        ("SS", "Short Story"),
        ("PM", "Poem"),
        ("PL", "Play"),
        ("SC", "Script"),  # Screenplay, teleplay, etc.
        ("MG", "Manga"),
        ("CM", "Comic"),
        ("CL", "Children's"),
        ("FL", "Folktale"),
        # nonfictions
        ("NF", "Nonfiction"),
        ("ES", "Essay"),
        ("TB", "Textbook"),
        ("GU", "Guidebook"),
        ("AR", "Article"),
        ("SH", "Speech"),
        ("LG", "Lecture"),
        ("IN", "Interview"),
        ("RE", "Review"),
        ("LT", "Letter"),
        ("RP", "Research Paper"),
        ("TS", "Thesis"),
        ("DS", "Dissertation"),
        ("OT", "Other"),
    )
    work_type = models.CharField(
        max_length=255, choices=WORK_TYPES, blank=True, null=True
    )  # novel, etc.
    genres = models.ManyToManyField(Genre, related_name="read_works", blank=True)
    wikipedia = models.URLField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # based on
    based_on_litworks = models.ManyToManyField(
        "self", blank=True, symmetrical=False, related_name="related_publications"
    )
    based_on_games = models.ManyToManyField(
        "play.Work", blank=True, related_name="publications"
    )
    based_on_movies = models.ManyToManyField(
        "watch.Movie", blank=True, related_name="publications"
    )
    based_on_series = models.ManyToManyField(
        "watch.Series", blank=True, related_name="publications"
    )

    # mentions
    mentioned_litworks = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="mentioned_in_publications",
    )
    mentioned_litinstances = models.ManyToManyField(
        "read.Instance", blank=True, related_name="mentioned_in_publications"
    )
    mentioned_books = models.ManyToManyField(
        "read.Book", blank=True, related_name="mentioned_in_publications"
    )
    mentioned_periodicals = models.ManyToManyField(
        "read.Periodical", blank=True, related_name="mentioned_in_publications"
    )
    mentioned_issues = models.ManyToManyField(
        "read.Issue", blank=True, related_name="mentioned_in_publications"
    )
    mentioned_gameworks = models.ManyToManyField(
        "play.Work", blank=True, related_name="mentioned_in_publications"
    )
    mentioned_games = models.ManyToManyField(
        "play.Game", blank=True, related_name="mentioned_in_publications"
    )
    mentioned_movies = models.ManyToManyField(
        "watch.Movie", blank=True, related_name="mentioned_in_publications"
    )
    mentioned_series = models.ManyToManyField(
        "watch.Series", blank=True, related_name="mentioned_in_publications"
    )
    mentioned_musicalworks = models.ManyToManyField(
        "listen.Work", blank=True, related_name="mentioned_in_publications"
    )
    mentioned_tracks = models.ManyToManyField(
        "listen.Track", blank=True, related_name="mentioned_in_publications"
    )
    mentioned_releases = models.ManyToManyField(
        "listen.Release", blank=True, related_name="mentioned_in_publications"
    )
    mentioned_locations = models.ManyToManyField(
        "visit.Location", blank=True, related_name="mentioned_in_publications"
    )

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="works_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="works_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    # Add history
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("read:work_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        # Convert the publication_date to a standard format if it's not None or empty
        if self.publication_date:
            self.publication_date = standardize_date(self.publication_date)

        is_new_instance = not self.pk
        if is_new_instance:
            super().save(*args, **kwargs)

        if self.related_locations.exists():
            related_locations_hierarchy = []
            for location in self.related_locations.all():
                related_locations_hierarchy += get_location_hierarchy_ids(location)
            self.related_locations_hierarchy = ",".join(
                set(related_locations_hierarchy)
            )

        super().save(*args, **kwargs)

    def model_name(self):
        return "Work"


class WorkRole(auto_prefetch.Model):  # Renamed from BookRole
    """
    A Role of a Creator in a Work
    """

    work = auto_prefetch.ForeignKey(Work, on_delete=models.CASCADE)
    creator = auto_prefetch.ForeignKey(
        Creator,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="read_workrole_set",
    )
    role = auto_prefetch.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="read_workrole_set",
    )
    alt_name = models.CharField(max_length=255, blank=True, null=True)

    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.work} - {self.creator} - {self.role}"


class Instance(auto_prefetch.Model):
    """
    An Instance is a manifestation of a Work,
    that is, a specific edition, a translation, an installment of a serialization, etc.
    """

    # admin
    locked = models.BooleanField(default=False)

    # instance meta
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    creators = models.ManyToManyField(
        Creator, through="InstanceRole", related_name="instances"
    )
    work = auto_prefetch.ForeignKey(
        Work, on_delete=models.SET_NULL, null=True, blank=True, related_name="instances"
    )
    publication_date = models.TextField(blank=True, null=True)
    language = LanguageField(max_length=8, blank=True, null=True)
    edition = models.CharField(
        max_length=255, blank=True, null=True
    )  # 1st ed., revised ed., etc.
    wikipedia = models.URLField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # based on / for marking the source of translation
    based_on_instances = models.ManyToManyField(
        "self", blank=True, symmetrical=False, related_name="related_instances"
    )

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="instances_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="instances_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("read:instance_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        # Convert the publication_date to a standard format if it's not None or empty
        if self.publication_date:
            self.publication_date = standardize_date(self.publication_date)
        super(Instance, self).save(*args, **kwargs)

    def model_name(self):
        return "Instance"


class InstanceRole(auto_prefetch.Model):
    instance = auto_prefetch.ForeignKey(Instance, on_delete=models.CASCADE)
    creator = auto_prefetch.ForeignKey(
        Creator, on_delete=models.CASCADE, null=True, blank=True
    )
    alt_name = models.CharField(max_length=255, blank=True, null=True)
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return f"{self.instance} - {self.creator} - {self.role}"


class Book(auto_prefetch.Model):
    """
    A Book entity of an Instance
    """

    # admin
    locked = models.BooleanField(default=False)

    # book meta data
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    cover = models.ImageField(upload_to=rename_book_cover, null=True, blank=True)
    cover_sens = models.BooleanField(default=False, null=True, blank=True)
    creators = models.ManyToManyField(Creator, through="BookRole", related_name="books")
    instances = models.ManyToManyField(
        Instance, through="BookInstance", related_name="books"
    )
    publisher = auto_prefetch.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        related_name="books",
        null=True,
        blank=True,
    )
    language = LanguageField(max_length=8, blank=True, null=True)
    publication_date = models.TextField(blank=True, null=True)
    wikipedia = models.URLField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

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
    votes = GenericRelation("discover.Vote")

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="books_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="books_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("read:book_detail", args=[str(self.id)])

    def get_genres(self):
        genres = set()
        for instance in self.instances.all():
            if instance.work:
                genres.update(instance.work.genres.all())
        return genres

    def model_name(self):
        return "Book"

    @property
    def checkin_count(self):
        return (
            self.readcheckin_set.count()
        )  # adjust this if your related name is different

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0

    def save(self, *args, **kwargs):
        # To hold a flag indicating if the cover is new or updated
        new_or_updated_cover = False

        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Book.objects.get(pk=self.pk)
            # If the cover has been updated
            if old_instance.cover != self.cover:
                # Delete the old cover
                old_instance.cover.delete(save=False)
                new_or_updated_cover = True
        else:
            new_or_updated_cover = True

        super().save(*args, **kwargs)

        if new_or_updated_cover and self.cover:
            img = Image.open(self.cover.open(mode="rb"))

            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)

            # Save the image to a BytesIO object
            temp_file = BytesIO()
            img.save(temp_file, format="WEBP")
            temp_file.seek(0)

            # Generate new name for the webp image
            webp_name = os.path.splitext(self.cover.name)[0] + ".webp"

            # remove the original image
            self.cover.delete(save=False)

            # Save the BytesIO object to the FileField
            self.cover.save(webp_name, ContentFile(temp_file.read()), save=False)

            img.close()
            self.cover.close()

        # Convert the publication_date to a standard format if it's not None or empty
        if self.publication_date:
            self.publication_date = standardize_date(self.publication_date)

        super().save(*args, **kwargs)


class BookRole(auto_prefetch.Model):
    book = auto_prefetch.ForeignKey(Book, on_delete=models.CASCADE)
    creator = auto_prefetch.ForeignKey(
        Creator,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_query_name="book_roles",
    )
    role = auto_prefetch.ForeignKey(
        Role, on_delete=models.CASCADE, null=True, blank=True
    )
    alt_name = models.CharField(max_length=255, blank=True, null=True)

    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return f"{self.book} - {self.alt_name or self.creator.name} - {self.role}"


class BookInstance(auto_prefetch.Model):
    book = auto_prefetch.ForeignKey(Book, on_delete=models.CASCADE)
    instance = auto_prefetch.ForeignKey(
        Instance, on_delete=models.CASCADE, null=True, blank=True
    )
    order = models.PositiveIntegerField(
        null=True, blank=True, default=1
    )  # Ordering of the works in a book

    # history = HistoricalRecords(inherit=True)

    class Meta(auto_prefetch.Model.Meta):
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


class ReadCheckIn(auto_prefetch.Model):
    content_type = auto_prefetch.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    user = auto_prefetch.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    STATUS_CHOICES = [
        ("to_read", "To Read"),
        ("reading", "Reading"),
        ("finished_reading", "Read"),
        ("paused", "Paused"),
        ("abandoned", "Abandoned"),
        ("rereading", "Rereading"),
        ("reread", "Reread"),
        ("afterthought", "Afterthought"),
        ("sampled", "Sampled"),
        ("skimmed", "Skimmed"),
    ]
    status = models.CharField(max_length=255, choices=STATUS_CHOICES)
    share_to_feed = models.BooleanField(default=False)
    content = models.TextField(
        null=True, blank=True
    )  # Any thoughts or comments at this check-in.
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    progress = models.CharField(max_length=20, null=True, blank=True)
    PAGE = "PG"
    PERCENTAGE = "PC"
    CHAPTER = "CH"
    PROGRESS_TYPE_CHOICES = [
        (PAGE, "Page"),
        (PERCENTAGE, "Percentage"),
        (CHAPTER, "Chapter"),
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
    votes = GenericRelation("discover.Vote")

    visibility = models.CharField(
        max_length=2,
        choices=Activity.VISIBILITY_CHOICES,
        default=Activity.VISIBILITY_PUBLIC,
    )

    visible_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="visible_read_checkins", blank=True
    )
    activities = GenericRelation(Activity, related_query_name="read_checkin_activity")

    def get_absolute_url(self):
        return reverse(
            "write:read_checkin_detail",
            kwargs={"pk": self.pk, "username": self.user.username},
        )

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="readcheckin", object_id=self.id
            )
            return activity.id
        except ObjectDoesNotExist:
            return None

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0

    @property
    def has_voted(self):
        return user_has_upvoted(self.user, self.content_object)

    def model_name(self):
        return "Read Check-In"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        was_updated = False
        super().save(*args, **kwargs)

        visible_to_users = set()

        if self.visibility == Activity.VISIBILITY_MENTIONED:
            visible_to_users.update(find_mentioned_users(self.content))
        elif self.visibility == Activity.VISIBILITY_FOLLOWERS:
            visible_to_users.update(
                self.user.followers.values_list("follower_id", flat=True)
            )
        elif self.visibility == Activity.VISIBILITY_PRIVATE:
            visible_to_users.add(self.user.id)

        # Always include self.user
        visible_to_users.add(self.user.id)

        self.visible_to.set(visible_to_users)

        # Attempt to fetch an existing Activity object for this check-in
        try:
            activity = Activity.objects.get(
                content_type__model="readcheckin",
                object_id=self.id,
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
                        content_type__model="readcheckin", object_id=self.id
                    )
                    activity.visibility = self.visibility
                    activity.save()  # This will trigger the update logic in Activity model
                except Activity.DoesNotExist:
                    pass  # Handle the case where the Activity object does not exist

            if is_new or activity is None:
                Activity.objects.create(
                    user=self.user,
                    activity_type="read-check-in",
                    content_object=self,
                    visibility=self.visibility,
                )

        elif activity is not None:
            # Optionally, remove the Activity if share_to_feed is False
            activity.delete()

        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


class Periodical(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # periodical meta data
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
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="periodicals_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="periodicals_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title


class Issue(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # issue meta data
    periodical = auto_prefetch.ForeignKey(
        Periodical, on_delete=models.CASCADE, related_name="issues"
    )
    publisher = auto_prefetch.ForeignKey(
        Company,
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
    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="issues_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="issues_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    history = HistoricalRecords(inherit=True)

    readcheckin = GenericRelation("ReadCheckIn")
    votes = GenericRelation("discover.Vote")

    def __str__(self):
        return f"{self.periodical.title} - Issue {self.number} - Volume {self.volume}"

    def get_absolute_url(self):
        return reverse(
            "read:issue_detail", args=[str(self.periodical.id), str(self.id)]
        )

    @property
    def checkin_count(self):
        return self.readcheckin_set.count()

    def get_votes(self):
        return self.votes.aggregate(models.Sum("value"))["value__sum"] or 0

    def save(self, *args, **kwargs):
        new_or_updated_cover = False

        # If the instance already exists in the database
        if self.pk:
            # Get the existing instance from the database
            old_instance = Issue.objects.get(pk=self.pk)
            # If the cover has been updated
            if old_instance.cover != self.cover:
                # Delete the old cover
                old_instance.cover.delete(save=False)
                new_or_updated_cover = True
        else:
            new_or_updated_cover = True

        super().save(*args, **kwargs)

        if new_or_updated_cover and self.cover:
            img = Image.open(self.cover.open(mode="rb"))

            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)

            # Save the image to a BytesIO object
            temp_file = BytesIO()
            img.save(temp_file, format="WEBP")
            temp_file.seek(0)

            # Generate new name for the webp image
            webp_name = os.path.splitext(self.cover.name)[0] + ".webp"

            # remove the original image
            self.cover.delete(save=False)

            # Save the BytesIO object to the FileField
            self.cover.save(webp_name, ContentFile(temp_file.read()), save=False)

            img.close()
            self.cover.close()

        # Convert the publication_date to a standard format if it's not None or empty
        if self.publication_date:
            self.publication_date = standardize_date(self.publication_date)

        if self.title is None:
            self.title = f"Vol. {self.volume} Nr. {self.number}"

        super().save(*args, **kwargs)


class IssueInstance(auto_prefetch.Model):
    issue = auto_prefetch.ForeignKey(Issue, on_delete=models.CASCADE)
    instance = auto_prefetch.ForeignKey(
        Instance, on_delete=models.CASCADE, null=True, blank=True
    )
    order = models.PositiveIntegerField(
        null=True, blank=True, default=1
    )  # Ordering of the works in a book

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["order"]

    def __str__(self):
        return f"{self.issue} - {self.instance} - {self.order}"


class BookSeries(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # series meta data
    title = models.CharField(max_length=100)
    books = models.ManyToManyField(Book, through="BookInSeries", related_name="series")
    notes = models.TextField(null=True, blank=True)

    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="bookseries_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="bookseries_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("read:series_detail", args=[str(self.id)])


class BookInSeries(auto_prefetch.Model):
    book = auto_prefetch.ForeignKey(Book, on_delete=models.CASCADE)
    series = auto_prefetch.ForeignKey(BookSeries, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    history = HistoricalRecords(inherit=True)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["order"]

    def __str__(self):
        return f"{self.series.title}: {self.book.title}"


class BookGroup(auto_prefetch.Model):
    # admin
    locked = models.BooleanField(default=False)

    # book group meta
    title = models.CharField(max_length=100)
    books = models.ManyToManyField(
        Book, through="BookInGroup", related_name="book_group"
    )

    created_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="bookgroup_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="bookgroup_updated",
        on_delete=models.SET_NULL,
        null=True,
    )
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("read:bookgroup_detail", args=[str(self.id)])


class BookInGroup(auto_prefetch.Model):
    book = auto_prefetch.ForeignKey(Book, on_delete=models.CASCADE)
    group = auto_prefetch.ForeignKey(BookGroup, on_delete=models.CASCADE)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["book__publication_date"]

    def __str__(self):
        return f"{self.group.title}: {self.book.title}"
