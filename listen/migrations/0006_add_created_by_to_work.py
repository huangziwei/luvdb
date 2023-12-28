from django.contrib.auth import get_user_model
from django.db import migrations
from django.utils import timezone


def update_work_model(apps, schema_editor):
    Work = apps.get_model("listen", "Work")

    CustomUser = apps.get_model("accounts", "CustomUser")
    user = CustomUser.objects.filter(is_superuser=True).first()

    for work in Work.objects.filter(created_by__isnull=True, updated_by__isnull=True):
        work.created_at = work.created_at or timezone.now()
        work.updated_at = work.updated_at or timezone.now()
        work.created_by = work.created_by or user
        work.updated_by = work.updated_by or user
        work.save()


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0005_historicalwork_created_at_historicalwork_created_by_and_more"),
    ]

    operations = [
        migrations.RunPython(update_work_model),
    ]
