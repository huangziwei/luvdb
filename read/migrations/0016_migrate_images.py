import django.contrib.contenttypes.models
import django.core.files.storage
from django.db import migrations, models


def migrate_book_covers(apps, schema_editor):
    """
    Moves all existing book cover images to the CoverAlbum model.
    """
    Book = apps.get_model("read", "Book")
    CoverAlbum = apps.get_model("entity", "CoverAlbum")
    CoverImage = apps.get_model("entity", "CoverImage")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = ContentType.objects.get_for_model(Book)

    for book in Book.objects.exclude(cover="").exclude(cover__isnull=True):
        # Create a CoverAlbum for this Book
        cover_album, created = CoverAlbum.objects.get_or_create(
            content_type=content_type,
            object_id=book.id,
        )

        # Move the cover image to CoverAlbum
        CoverImage.objects.create(
            cover_album=cover_album,
            image=book.cover,
            is_primary=True,
        )

        print(f"✅ Moved cover for Book: {book.title} (ID: {book.id})")


class Migration(migrations.Migration):

    dependencies = [
        ("read", "0015_historicalissuerole_issuerole_issue_creators"),  # Replace with the last migration file
    ]

    operations = [
        migrations.RunPython(migrate_book_covers, reverse_code=migrations.RunPython.noop),
    ]
