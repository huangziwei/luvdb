# Generated by Django 5.0 on 2023-12-08 16:12

import auto_prefetch
import autoslug.fields
import django.db.models.deletion
import django.db.models.manager
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("activity_feed", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
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
                ("name", models.CharField(max_length=50, unique=True)),
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
        migrations.CreateModel(
            name="Comment",
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
                ("content", models.TextField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("object_id", models.PositiveIntegerField()),
                ("anchor", models.CharField(blank=True, max_length=4)),
                (
                    "content_type",
                    auto_prefetch.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "user",
                    auto_prefetch.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
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
        migrations.CreateModel(
            name="LuvList",
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
                ("title", models.CharField(max_length=100)),
                ("notes", models.TextField(blank=True, null=True)),
                ("source", models.URLField(blank=True, null=True)),
                ("wikipedia", models.URLField(blank=True, null=True)),
                (
                    "order_preference",
                    models.CharField(
                        choices=[("ASC", "Ascending"), ("DESC", "Descending")],
                        default="ASC",
                        max_length=4,
                    ),
                ),
                ("allow_collaboration", models.BooleanField(default=False)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "collaborators",
                    models.ManyToManyField(
                        blank=True,
                        related_name="collaborated_luvlists",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    auto_prefetch.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="luvlists_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("tags", models.ManyToManyField(blank=True, to="write.tag")),
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
        migrations.CreateModel(
            name="ContentInList",
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
                ("order", models.PositiveIntegerField(blank=True, null=True)),
                ("object_id", models.PositiveIntegerField()),
                ("comment", models.TextField(blank=True, null=True)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "content_type",
                    auto_prefetch.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "luv_list",
                    auto_prefetch.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contents",
                        to="write.luvlist",
                    ),
                ),
            ],
            options={
                "ordering": ["order"],
                "abstract": False,
                "base_manager_name": "prefetch_manager",
            },
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name="Project",
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
                ("name", models.CharField(max_length=50)),
                ("slug", models.SlugField(blank=True, editable=False)),
                (
                    "order",
                    models.CharField(
                        choices=[
                            ("NF", "Newest first"),
                            ("OF", "Oldest first"),
                            ("BT", "By title"),
                        ],
                        default="NF",
                        max_length=2,
                    ),
                ),
                (
                    "user",
                    auto_prefetch.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
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
        migrations.CreateModel(
            name="Randomizer",
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
                    "last_generated_datetime",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("randomized_order", models.TextField(blank=True, null=True)),
                ("interval_in_seconds", models.IntegerField(default=86400)),
                (
                    "last_generated_item",
                    auto_prefetch.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="randomized_in",
                        to="write.contentinlist",
                    ),
                ),
                (
                    "luv_list",
                    auto_prefetch.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="randomizers",
                        to="write.luvlist",
                    ),
                ),
                (
                    "user",
                    auto_prefetch.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
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
        migrations.CreateModel(
            name="Say",
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
                ("content", models.TextField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("comments_enabled", models.BooleanField(default=True)),
                ("is_direct_mention", models.BooleanField(default=False)),
                (
                    "user",
                    auto_prefetch.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "visible_to",
                    models.ManyToManyField(
                        blank=True,
                        related_name="visible_says",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("tags", models.ManyToManyField(blank=True, to="write.tag")),
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
        migrations.CreateModel(
            name="Repost",
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
                ("content", models.TextField(blank=True)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("comments_enabled", models.BooleanField(default=True)),
                ("object_id", models.PositiveIntegerField()),
                (
                    "content_type",
                    auto_prefetch.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "original_activity",
                    auto_prefetch.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reposts",
                        to="activity_feed.activity",
                    ),
                ),
                (
                    "original_repost",
                    auto_prefetch.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reposts",
                        to="write.repost",
                    ),
                ),
                (
                    "user",
                    auto_prefetch.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("tags", models.ManyToManyField(blank=True, to="write.tag")),
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
        migrations.CreateModel(
            name="Post",
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
                ("title", models.CharField(max_length=200)),
                ("content", models.TextField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("comments_enabled", models.BooleanField(default=True)),
                (
                    "slug",
                    autoslug.fields.AutoSlugField(
                        allow_unicode=True,
                        editable=False,
                        null=True,
                        populate_from="title",
                        unique=True,
                    ),
                ),
                ("share_to_feed", models.BooleanField(default=False)),
                (
                    "user",
                    auto_prefetch.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("projects", models.ManyToManyField(blank=True, to="write.project")),
                ("tags", models.ManyToManyField(blank=True, to="write.tag")),
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
        migrations.CreateModel(
            name="Pin",
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
                ("title", models.TextField()),
                ("url", models.URLField()),
                ("content", models.TextField(blank=True, null=True)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("comments_enabled", models.BooleanField(default=True)),
                ("share_to_feed", models.BooleanField(default=False)),
                (
                    "user",
                    auto_prefetch.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("tags", models.ManyToManyField(blank=True, to="write.tag")),
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
