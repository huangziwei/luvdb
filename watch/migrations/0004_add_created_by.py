from django.contrib.auth import get_user_model
from django.db import migrations
from django.utils import timezone


def update_episode_model(apps, schema_editor):
    Episode = apps.get_model("watch", "Episode")

    CustomUser = apps.get_model("accounts", "CustomUser")
    user = CustomUser.objects.filter(is_superuser=True).first()

    for episode in Episode.objects.filter(
        created_by__isnull=True, updated_by__isnull=True
    ):
        episode.created_at = episode.created_at or timezone.now()
        episode.updated_at = episode.updated_at or timezone.now()
        episode.created_by = episode.created_by or user
        episode.updated_by = episode.updated_by or user
        episode.save()


class Migration(migrations.Migration):
    dependencies = [
        ("watch", "0003_episode_created_at_episode_created_by_and_more"),
    ]

    operations = [
        migrations.RunPython(update_episode_model),
    ]
