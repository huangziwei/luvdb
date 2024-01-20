# Generated by Django 5.0.1 on 2024-01-16 20:47

import auto_prefetch
import django.db.models.deletion
import django.db.models.manager
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("entity", "0008_remove_company_parent_remove_company_successor_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MemberOf",
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
                ("notes", models.CharField(blank=True, max_length=100, null=True)),
                ("start_date", models.CharField(blank=True, max_length=10, null=True)),
                ("end_date", models.CharField(blank=True, max_length=10, null=True)),
                (
                    "creator",
                    auto_prefetch.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="member_of",
                        to="entity.creator",
                    ),
                ),
                (
                    "group",
                    auto_prefetch.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="entity.creator",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "prefetch_manager",
            },
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
    ]