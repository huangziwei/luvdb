# Generated by Django 4.2.2 on 2023-10-06 15:56

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("write", "0016_luvlist_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="say",
            name="is_direct_mention",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="say",
            name="visible_to",
            field=models.ManyToManyField(
                blank=True, related_name="visible_says", to=settings.AUTH_USER_MODEL
            ),
        ),
    ]