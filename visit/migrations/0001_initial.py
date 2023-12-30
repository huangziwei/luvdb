# Generated by Django 5.0 on 2023-12-30 19:31

import auto_prefetch
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Location",
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
                ("locked", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255, unique=True)),
                ("other_names", models.TextField(blank=True, null=True)),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("continent", "Continent"),
                            ("polity", "Polity"),
                            ("region", "Region"),
                            ("city", "City"),
                            ("town", "Town"),
                            ("village", "Village"),
                            ("neighborhood", "Neighborhood"),
                            ("poi", "Point of Interest"),
                        ],
                        max_length=20,
                    ),
                ),
                ("historical", models.BooleanField(default=False)),
                (
                    "historical_period",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("address", models.TextField(blank=True, null=True)),
                ("wikipedia", models.URLField(blank=True, null=True)),
                ("website", models.URLField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    auto_prefetch.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="locations_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="children",
                        to="visit.location",
                    ),
                ),
                (
                    "updated_by",
                    auto_prefetch.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="locations_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
