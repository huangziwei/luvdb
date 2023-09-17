# Generated by Django 4.2.2 on 2023-09-16 09:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("play", "0030_remove_game_developers_remove_game_publishers_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="GameCompany",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("other_names", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("location", models.CharField(blank=True, max_length=100, null=True)),
                ("website", models.URLField(blank=True, null=True)),
                ("wikipedia", models.URLField(blank=True, null=True)),
                (
                    "founded_date",
                    models.CharField(blank=True, max_length=10, null=True),
                ),
                ("closed_date", models.CharField(blank=True, max_length=10, null=True)),
                ("notes", models.TextField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="game",
            name="developers",
            field=models.ManyToManyField(
                related_name="developed_games", to="play.gamecompany"
            ),
        ),
        migrations.AddField(
            model_name="game",
            name="publishers",
            field=models.ManyToManyField(
                related_name="published_games", to="play.gamecompany"
            ),
        ),
        migrations.AddField(
            model_name="work",
            name="developers",
            field=models.ManyToManyField(
                related_name="play_works", to="play.gamecompany"
            ),
        ),
    ]