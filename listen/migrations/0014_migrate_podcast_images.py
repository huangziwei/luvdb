from django.db import migrations


def migrate_podcast_covers(apps, schema_editor):
    """
    Moves all existing podcast cover images to the CoverAlbum model.
    """
    Podcast = apps.get_model("listen", "Podcast")
    CoverAlbum = apps.get_model("entity", "CoverAlbum")
    CoverImage = apps.get_model("entity", "CoverImage")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = ContentType.objects.get_for_model(Podcast)

    for podcast in Podcast.objects.exclude(cover="").exclude(cover__isnull=True):
        # Create a CoverAlbum for this Podcast
        cover_album, created = CoverAlbum.objects.get_or_create(
            content_type=content_type,
            object_id=podcast.id,
        )

        # Move the cover image to CoverAlbum
        CoverImage.objects.create(
            cover_album=cover_album,
            image=podcast.cover,
            is_primary=True,
        )

        print(f"✅ Moved cover for Podcast: {podcast.title} (ID: {podcast.id})")


class Migration(migrations.Migration):

    dependencies = [
        ("listen", "0013_migrate_audiobook_images"),  # Replace with the last migration file
    ]

    operations = [
        migrations.RunPython(migrate_podcast_covers, reverse_code=migrations.RunPython.noop),
    ]
