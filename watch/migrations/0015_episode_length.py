# Generated by Django 4.2.2 on 2023-08-16 08:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("watch", "0014_episode_other_titles_movie_other_titles_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="episode",
            name="length",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
