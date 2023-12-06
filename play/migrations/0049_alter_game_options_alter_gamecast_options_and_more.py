# Generated by Django 4.2.2 on 2023-12-06 13:27

import auto_prefetch
from django.conf import settings
from django.db import migrations
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):
    dependencies = [
        ("entity", "0019_alter_company_options_alter_creator_options_and_more"),
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("play", "0048_remove_playcheckin_game"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="game",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="gamecast",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="gameinseries",
            options={"base_manager_name": "prefetch_manager", "ordering": ["order"]},
        ),
        migrations.AlterModelOptions(
            name="gamereleasedate",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="gamerole",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="gameseries",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="genre",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="platform",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="playcheckin",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="work",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="workrole",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelManagers(
            name="game",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="gamecast",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="gameinseries",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="gamereleasedate",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="gamerole",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="gameseries",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="genre",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="platform",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="playcheckin",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="work",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="workrole",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterField(
            model_name="game",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="games_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="game",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="games_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="game",
            name="work",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="games",
                to="play.work",
            ),
        ),
        migrations.AlterField(
            model_name="gamecast",
            name="creator",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="entity.creator",
            ),
        ),
        migrations.AlterField(
            model_name="gamecast",
            name="game",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="gamecasts",
                to="play.game",
            ),
        ),
        migrations.AlterField(
            model_name="gamecast",
            name="role",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="entity.role",
            ),
        ),
        migrations.AlterField(
            model_name="gameinseries",
            name="game",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="play.game"
            ),
        ),
        migrations.AlterField(
            model_name="gameinseries",
            name="series",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="play.gameseries"
            ),
        ),
        migrations.AlterField(
            model_name="gamereleasedate",
            name="game",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="region_release_dates",
                to="play.game",
            ),
        ),
        migrations.AlterField(
            model_name="gamerole",
            name="creator",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="entity.creator",
            ),
        ),
        migrations.AlterField(
            model_name="gamerole",
            name="game",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="gameroles",
                to="play.game",
            ),
        ),
        migrations.AlterField(
            model_name="gamerole",
            name="role",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="entity.role",
            ),
        ),
        migrations.AlterField(
            model_name="gameseries",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="series_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="gameseries",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="series_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="historicalgame",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="historicalgame",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="historicalgame",
            name="work",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="play.work",
            ),
        ),
        migrations.AlterField(
            model_name="historicalgamecast",
            name="creator",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="entity.creator",
            ),
        ),
        migrations.AlterField(
            model_name="historicalgamecast",
            name="game",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="play.game",
            ),
        ),
        migrations.AlterField(
            model_name="historicalgamecast",
            name="role",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="entity.role",
            ),
        ),
        migrations.AlterField(
            model_name="historicalgamereleasedate",
            name="game",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="play.game",
            ),
        ),
        migrations.AlterField(
            model_name="historicalgamerole",
            name="creator",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="entity.creator",
            ),
        ),
        migrations.AlterField(
            model_name="historicalgamerole",
            name="game",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="play.game",
            ),
        ),
        migrations.AlterField(
            model_name="historicalgamerole",
            name="role",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="entity.role",
            ),
        ),
        migrations.AlterField(
            model_name="historicalgameseries",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="historicalgameseries",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="historicalplatform",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="historicalplatform",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="historicalwork",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="historicalwork",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="platform",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="platform",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="playcheckin",
            name="content_type",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AlterField(
            model_name="playcheckin",
            name="user",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AlterField(
            model_name="work",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="play_works_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="work",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="play_works_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="workrole",
            name="creator",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="play_workrole_set",
                to="entity.creator",
            ),
        ),
        migrations.AlterField(
            model_name="workrole",
            name="role",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="play_workrole_set",
                to="entity.role",
            ),
        ),
        migrations.AlterField(
            model_name="workrole",
            name="work",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="play.work"
            ),
        ),
    ]