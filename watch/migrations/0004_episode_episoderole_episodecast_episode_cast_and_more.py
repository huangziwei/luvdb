# Generated by Django 4.2.2 on 2023-07-03 19:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("entity", "0001_initial"),
        ("watch", "0003_series_rename_death_date_studio_closed_date_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Episode",
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
                ("title", models.CharField(blank=True, max_length=255, null=True)),
                ("season", models.IntegerField(blank=True, null=True)),
                ("episode", models.IntegerField(blank=True, null=True)),
                (
                    "release_date",
                    models.CharField(blank=True, max_length=10, null=True),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EpisodeRole",
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
                ("alt_name", models.CharField(blank=True, max_length=100, null=True)),
                (
                    "episode",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="episodesroles",
                        to="watch.episode",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="entity.person",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="entity.role",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EpisodeCast",
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
                (
                    "character_name",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "episode",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="episodecasts",
                        to="watch.episode",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="entity.person",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="entity.role",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="episode",
            name="cast",
            field=models.ManyToManyField(
                related_name="episodes_cast",
                through="watch.EpisodeCast",
                to="entity.person",
            ),
        ),
        migrations.AddField(
            model_name="episode",
            name="persons",
            field=models.ManyToManyField(
                related_name="episodes_role",
                through="watch.EpisodeRole",
                to="entity.person",
            ),
        ),
        migrations.AddField(
            model_name="episode",
            name="series",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="episodes",
                to="watch.series",
            ),
        ),
    ]
