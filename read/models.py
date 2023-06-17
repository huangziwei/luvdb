import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from PIL import Image


# helpers
def rename_edition_cover(instance, filename):
    base, extension = os.path.splitext(filename)
    new_name = f"{slugify(instance.edition_title, allow_unicode=True)}-{instance.publication_date}{extension}"
    return os.path.join("covers/", new_name)


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
    bio = models.TextField(blank=True, null=True)
    birth_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    death_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD

    def __str__(self):
        return self.name


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


class Role(models.Model):
    """
    A Role of a Person
    """

    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # captialize letter of each word
        self.name = " ".join([word.capitalize() for word in self.name.split()])
        return super(Role, self).save(*args, **kwargs)


class Book(models.Model):
    """
    A Book entity
    """

    # book meta data
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    persons = models.ManyToManyField(Person, through="BookRole", related_name="books")
    publication_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD

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


class BookRole(models.Model):
    """
    A Role of a Person in a Book
    """

    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.book} - {self.person} - {self.role}"


class Edition(models.Model):
    """
    An Edition entity of a Book
    """

    # edition meta data
    edition_title = models.CharField(max_length=255)
    cover = models.ImageField(upload_to=rename_edition_cover, null=True, blank=True)
    book = models.ForeignKey(
        Book, on_delete=models.SET_NULL, related_name="editions", null=True, blank=True
    )
    persons = models.ManyToManyField(
        Person, through="EditionRole", related_name="editions"
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        related_name="editions",
        null=True,
        blank=True,
    )
    language = models.CharField(max_length=255, blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    publication_date = models.CharField(
        max_length=10, blank=True, null=True
    )  # YYYY or YYYY-MM or YYYY-MM-DD
    edition_format = models.CharField(
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
        related_name="editions_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="editions_updated",
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return self.edition_title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.cover:
            img = Image.open(self.cover.path)

            if img.height > 500 or img.width > 500:
                output_size = (500, 500)
                img.thumbnail(output_size)
                img.save(self.cover.path)


class EditionRole(models.Model):
    edition = models.ForeignKey(Edition, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.edition} - {self.name or self.person.name} - {self.role}"
