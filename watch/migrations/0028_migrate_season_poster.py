import django.contrib.contenttypes.models
import django.core.files.storage
from django.db import migrations, models


def migrate_movie_posters(apps, schema_editor):
    """
    Moves all existing movie poster images to the CoverAlbum model.
    """
    Season = apps.get_model("watch", "Season")
    CoverAlbum = apps.get_model("entity", "CoverAlbum")
    CoverImage = apps.get_model("entity", "CoverImage")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = ContentType.objects.get_for_model(Season)

    for season in Season.objects.exclude(poster="").exclude(poster__isnull=True):
        # Create a CoverAlbum for this Season
        cover_album, created = CoverAlbum.objects.get_or_create(
            content_type=content_type,
            object_id=season.id,
        )

        # Move the cover image to CoverAlbum
        CoverImage.objects.create(
            cover_album=cover_album,
            image=season.poster,
            is_primary=True,
        )

        print(f"✅ Moved cover for Season: {season.title} (ID: {season.id})")


class Migration(migrations.Migration):

    dependencies = [
        ("watch", "0027_migrate_movie_poster"),  # Replace with the last migration file
    ]

    operations = [
        migrations.RunPython(migrate_movie_posters, reverse_code=migrations.RunPython.noop),
    ]
