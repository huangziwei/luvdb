import django.contrib.contenttypes.models
import django.core.files.storage
from django.db import migrations, models


def migrate_book_covers(apps, schema_editor):
    """
    Moves all existing book cover images to the CoverAlbum model.
    """
    Game = apps.get_model("play", "Game")
    CoverAlbum = apps.get_model("entity", "CoverAlbum")
    CoverImage = apps.get_model("entity", "CoverImage")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = ContentType.objects.get_for_model(Game)

    for game in Game.objects.exclude(cover="").exclude(cover__isnull=True):
        # Create a CoverAlbum for this Game
        cover_album, created = CoverAlbum.objects.get_or_create(
            content_type=content_type,
            object_id=game.id,
        )

        # Move the cover image to CoverAlbum
        CoverImage.objects.create(
            cover_album=cover_album,
            image=game.cover,
            is_primary=True,
        )

        print(f"✅ Moved cover for Game: {game.title} (ID: {game.id})")


class Migration(migrations.Migration):

    dependencies = [
        ("play", "0012_remove_historicalgame_work"),  # Replace with the last migration file
    ]

    operations = [
        migrations.RunPython(migrate_book_covers, reverse_code=migrations.RunPython.noop),
    ]
