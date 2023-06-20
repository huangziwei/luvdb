from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


# Create your models here.
class Entity(models.Model):
    """
    An Entity base model
    """

    # entity meta data
    name = models.CharField(max_length=255)
    romanized_name = models.CharField(max_length=255, blank=True, null=True)

    # entry meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="%(class)s_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="%(class)s_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Person(Entity):
    """
    A Person entity
    """

    # person meta data
    birth_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    death_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    birth_place = models.CharField(max_length=255, blank=True, null=True)
    death_place = models.CharField(max_length=255, blank=True, null=True)
    wikipedia = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name


class Role(models.Model):
    DOMAIN_CHOICES = (
        ("read", "Read"),
        ("listen", "Listen"),
        ("watch", "Watch"),
        ("play", "Play"),
        # Add more domains as needed
    )

    name = models.CharField(max_length=255, unique=True)
    domain = models.CharField(max_length=20, choices=DOMAIN_CHOICES)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = " ".join([word.capitalize() for word in self.name.split()])
        return super(Role, self).save(*args, **kwargs)


class Award(Entity):
    """
    An Award entity
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    # Define the generic foreign key
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        unique_together = ["name", "content_type", "object_id"]

    def __str__(self):
        return self.name


class AwardRecipient(models.Model):
    """
    A Recipient of an Award
    """

    award = models.ForeignKey(Award, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=[("N", "Nominated"), ("S", "Shortlisted"), ("W", "Won")]
    )
    year = models.PositiveIntegerField()

    # from `read` app
    work = models.ForeignKey("read.Work", on_delete=models.CASCADE)
    book = models.ForeignKey("read.Book", on_delete=models.CASCADE)

    # from `listen` app
    release = models.ForeignKey("listen.Release", on_delete=models.CASCADE)
    track = models.ForeignKey("listen.Track", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.person.name} - {self.award.name} ({self.get_status_display()})"
