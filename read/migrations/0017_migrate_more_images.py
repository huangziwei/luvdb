from django.db import migrations


def migrate_issue_covers(apps, schema_editor):
    """
    Moves all existing issue cover images to the CoverAlbum model.
    """
    Issue = apps.get_model("read", "Issue")
    CoverAlbum = apps.get_model("entity", "CoverAlbum")
    CoverImage = apps.get_model("entity", "CoverImage")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = ContentType.objects.get_for_model(Issue)

    for issue in Issue.objects.exclude(cover="").exclude(cover__isnull=True):
        # Create a CoverAlbum for this Issue
        cover_album, created = CoverAlbum.objects.get_or_create(
            content_type=content_type,
            object_id=issue.id,
        )

        # Move the cover image to CoverAlbum
        CoverImage.objects.create(
            cover_album=cover_album,
            image=issue.cover,
            is_primary=True,
        )

        print(f"✅ Moved cover for Issue: {issue.title} (ID: {issue.id})")


class Migration(migrations.Migration):

    dependencies = [
        ("read", "0016_migrate_images"),  # Replace with the last migration file
    ]

    operations = [
        migrations.RunPython(migrate_issue_covers, reverse_code=migrations.RunPython.noop),
    ]
