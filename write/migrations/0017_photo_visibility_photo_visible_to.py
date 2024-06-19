# Generated by Django 5.0.1 on 2024-06-19 12:56

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("write", "0016_luvlist_visibility_luvlist_visible_to"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="photo",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("PU", "Public"),
                    ("ME", "Mentioned People Only"),
                    ("FO", "Followers Only"),
                    ("PR", "Private"),
                ],
                default="PU",
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name="photo",
            name="visible_to",
            field=models.ManyToManyField(
                blank=True, related_name="visible_photos", to=settings.AUTH_USER_MODEL
            ),
        ),
    ]