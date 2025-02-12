import django.contrib.contenttypes.models
import django.core.files.storage
from django.db import migrations, models


def migrate_movie_posters(apps, schema_editor):
    """
    Moves all existing movie poster images to the CoverAlbum model.
    """
    Movie = apps.get_model("watch", "Movie")
    CoverAlbum = apps.get_model("entity", "CoverAlbum")
    CoverImage = apps.get_model("entity", "CoverImage")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = ContentType.objects.get_for_model(Movie)

    for movie in Movie.objects.exclude(poster="").exclude(poster__isnull=True):
        # Create a CoverAlbum for this Movie
        cover_album, created = CoverAlbum.objects.get_or_create(
            content_type=content_type,
            object_id=movie.id,
        )

        # Move the cover image to CoverAlbum
        CoverImage.objects.create(
            cover_album=cover_album,
            image=movie.poster,
            is_primary=True,
        )

        print(f"✅ Moved cover for Book: {movie.title} (ID: {movie.id})")


class Migration(migrations.Migration):

    dependencies = [
        ("watch", "0026_episodecast_is_star_episodecast_order_and_more"),  # Replace with the last migration file
    ]

    operations = [
        migrations.RunPython(migrate_movie_posters, reverse_code=migrations.RunPython.noop),
    ]
