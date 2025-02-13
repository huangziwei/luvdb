import django.contrib.contenttypes.models
import django.core.files.storage
from django.db import migrations, models


def migrate_book_covers(apps, schema_editor):
    """
    Moves all existing release cover images to the CoverAlbum model.
    """
    Release = apps.get_model("listen", "Release")
    CoverAlbum = apps.get_model("entity", "CoverAlbum")
    CoverImage = apps.get_model("entity", "CoverImage")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = ContentType.objects.get_for_model(Release)

    for release in Release.objects.exclude(cover="").exclude(cover__isnull=True):
        # Create a CoverAlbum for this Release
        cover_album, created = CoverAlbum.objects.get_or_create(
            content_type=content_type,
            object_id=release.id,
        )

        # Move the cover image to CoverAlbum
        CoverImage.objects.create(
            cover_album=cover_album,
            image=release.cover,
            is_primary=True,
        )

        print(f"✅ Moved cover for Release: {release.title} (ID: {release.id})")


class Migration(migrations.Migration):

    dependencies = [
        ("listen", "0011_listencheckin_visibility_listencheckin_visible_to"),  # Replace with the last migration file
    ]

    operations = [
        migrations.RunPython(migrate_book_covers, reverse_code=migrations.RunPython.noop),
    ]
