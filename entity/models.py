from django.conf import settings
from django.db import models
from django.urls import reverse


# Create your models here.
class Entity(models.Model):
    """
    An Entity base model
    """

    # entity meta data
    name = models.CharField(max_length=255)
    # romanized_name = models.CharField(max_length=255, blank=True, null=True)
    other_names = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

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

    def get_absolute_url(self):
        return reverse("entity:person_detail", kwargs={"pk": self.pk})


class Role(models.Model):
    DOMAIN_CHOICES = (
        ("read", "Read"),
        ("listen", "Listen"),
        ("watch", "Watch"),
        ("play", "Play"),
        # Add more domains as needed
    )

    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=20, choices=DOMAIN_CHOICES)

    class Meta:
        unique_together = ("name", "domain")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = " ".join([word.capitalize() for word in self.name.split()])
        return super(Role, self).save(*args, **kwargs)
