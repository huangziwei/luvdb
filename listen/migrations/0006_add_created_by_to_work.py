from django.contrib.auth import get_user_model
from django.db import migrations
from django.utils import timezone


def update_work_model(apps, schema_editor):
    Work = apps.get_model("listen", "Work")

    CustomUser = apps.get_model("accounts", "CustomUser")
    user = CustomUser.objects.get(pk=1)

    for work in Work.objects.all():
        work.created_at = timezone.now()
        work.updated_at = timezone.now()
        work.created_by = user
        work.updated_by = user
        work.save()


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0005_historicalwork_created_at_historicalwork_created_by_and_more"),
    ]

    operations = [
        migrations.RunPython(update_work_model),
    ]
