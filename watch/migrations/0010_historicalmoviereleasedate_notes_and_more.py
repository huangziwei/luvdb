# Generated by Django 5.0.1 on 2024-01-15 15:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("watch", "0009_alter_movie_based_on_movies_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalmoviereleasedate",
            name="notes",
            field=models.CharField(blank=True, max_length=300, null=True),
        ),
        migrations.AddField(
            model_name="historicalmoviereleasedate",
            name="release_type",
            field=models.CharField(
                choices=[
                    ("PREMIERE", "Premiere"),
                    ("THEATRICAL", "Theatrical"),
                    ("DIGITAL", "Digital"),
                    ("PHYSICAL", "Physical"),
                    ("TV", "TV"),
                    ("OTHER", "Other"),
                ],
                default="THEATRICAL",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="moviereleasedate",
            name="notes",
            field=models.CharField(blank=True, max_length=300, null=True),
        ),
        migrations.AddField(
            model_name="moviereleasedate",
            name="release_type",
            field=models.CharField(
                choices=[
                    ("PREMIERE", "Premiere"),
                    ("THEATRICAL", "Theatrical"),
                    ("DIGITAL", "Digital"),
                    ("PHYSICAL", "Physical"),
                    ("TV", "TV"),
                    ("OTHER", "Other"),
                ],
                default="THEATRICAL",
                max_length=10,
            ),
        ),
    ]