# Generated by Django 5.0.1 on 2024-06-19 17:22

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("play", "0009_game_ending_songs_game_soundtracks_game_theme_songs_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="playcheckin",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("PU", "Public"),
                    ("ME", "Mentioned"),
                    ("FO", "Followers"),
                    ("PR", "Private"),
                ],
                default="PU",
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name="playcheckin",
            name="visible_to",
            field=models.ManyToManyField(
                blank=True,
                related_name="visible_play_checkins",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
