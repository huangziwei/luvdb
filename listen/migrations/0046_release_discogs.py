# Generated by Django 4.2.2 on 2023-08-24 13:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0045_track_wikipedia"),
    ]

    operations = [
        migrations.AddField(
            model_name="release",
            name="discogs",
            field=models.URLField(blank=True, null=True),
        ),
    ]