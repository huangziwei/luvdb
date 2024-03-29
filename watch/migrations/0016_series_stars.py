# Generated by Django 5.0.1 on 2024-02-08 19:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("entity", "0011_alter_creator_active_years_and_more"),
        ("watch", "0015_movie_stars"),
    ]

    operations = [
        migrations.AddField(
            model_name="series",
            name="stars",
            field=models.ManyToManyField(
                blank=True, related_name="series_starred", to="entity.creator"
            ),
        ),
    ]
