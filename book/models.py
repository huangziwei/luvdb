from django.db import models


class Person(models.Model):
    name = models.CharField(max_length=200)
    alternative_names = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    date_of_death = models.DateField("Died", null=True, blank=True)
    biography = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def bibliography_as_author(self):
        return self.books_as_author.all()

    @property
    def bibliography_as_translator(self):
        return self.books_as_translator.all()


class Publisher(models.Model):
    name = models.CharField(max_length=200)
    website = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    authors = models.ManyToManyField(Person, related_name="books_as_author")
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, null=True, blank=True)
    synopsis = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title


class Series(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Edition(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="editions")
    series = models.ForeignKey(
        Series,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="editions",
    )
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True)
    translators = models.ManyToManyField(
        Person, related_name="books_as_translator", blank=True
    )

    isbn = models.CharField(max_length=13, unique=True)  # ISBN should be unique
    isbn_10 = models.CharField(max_length=10, unique=True, null=True, blank=True)
    publication_date = models.DateField()
    edition = models.CharField(
        max_length=200, null=True, blank=True
    )  # like "First Edition", "Reprint", "Translation" etc.
    edition_title = models.CharField(max_length=200)
    edition_subtitle = models.CharField(max_length=200, null=True, blank=True)

    price = models.CharField(
        max_length=200, null=True, blank=True
    )  # Price in USD for example

    language = models.CharField(max_length=50, null=True, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    book_format = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.edition_title}"
