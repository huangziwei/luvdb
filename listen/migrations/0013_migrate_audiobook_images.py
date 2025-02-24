from django.db import migrations


def migrate_audiobook_covers(apps, schema_editor):
    """
    Moves all existing audiobook cover images to the CoverAlbum model.
    """
    Audiobook = apps.get_model("listen", "Audiobook")
    CoverAlbum = apps.get_model("entity", "CoverAlbum")
    CoverImage = apps.get_model("entity", "CoverImage")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = ContentType.objects.get_for_model(Audiobook)

    for audiobook in Audiobook.objects.exclude(cover="").exclude(cover__isnull=True):
        # Create a CoverAlbum for this Audiobook
        cover_album, created = CoverAlbum.objects.get_or_create(
            content_type=content_type,
            object_id=audiobook.id,
        )

        # Move the cover image to CoverAlbum
        CoverImage.objects.create(
            cover_album=cover_album,
            image=audiobook.cover,
            is_primary=True,
        )

        print(f"✅ Moved cover for Audiobook: {audiobook.title} (ID: {audiobook.id})")


class Migration(migrations.Migration):

    dependencies = [
        ("listen", "0012_migrate_images"),  # Replace with the last migration file
    ]

    operations = [
        migrations.RunPython(migrate_audiobook_covers, reverse_code=migrations.RunPython.noop),
    ]
