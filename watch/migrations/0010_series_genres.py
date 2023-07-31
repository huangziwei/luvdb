# Generated by Django 4.2.2 on 2023-07-31 13:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("watch", "0009_genre_alter_watchcheckin_status_movie_genres"),
    ]

    operations = [
        migrations.AddField(
            model_name="series",
            name="genres",
            field=models.ManyToManyField(
                blank=True, related_name="series", to="watch.genre"
            ),
        ),
    ]