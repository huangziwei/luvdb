# Generated by Django 4.2.2 on 2023-07-05 13:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0016_release_apple_music_url_release_spotify_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="release",
            name="note",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="track",
            name="note",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="work",
            name="note",
            field=models.TextField(blank=True, null=True),
        ),
    ]