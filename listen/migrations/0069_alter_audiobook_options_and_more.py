# Generated by Django 4.2.2 on 2023-12-06 13:27

import auto_prefetch
from django.conf import settings
from django.db import migrations
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("read", "0049_delete_historicalbookinstance"),
        ("entity", "0019_alter_company_options_alter_creator_options_and_more"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("listen", "0068_listencheckin_updated_at"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="audiobook",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="audiobookinstance",
            options={"base_manager_name": "prefetch_manager", "ordering": ["order"]},
        ),
        migrations.AlterModelOptions(
            name="audiobookrole",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="genre",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="listencheckin",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="podcast",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="release",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="releasegroup",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="releaseingroup",
            options={
                "base_manager_name": "prefetch_manager",
                "ordering": ["release__release_date"],
            },
        ),
        migrations.AlterModelOptions(
            name="releaserole",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="releasetrack",
            options={
                "base_manager_name": "prefetch_manager",
                "ordering": ["disk", "order"],
            },
        ),
        migrations.AlterModelOptions(
            name="track",
            options={"base_manager_name": "prefetch_manager"},
        ),
        migrations.AlterModelOptions(
            name="trackrole",
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
            name="audiobook",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="audiobookinstance",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="audiobookrole",
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
            name="listencheckin",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="podcast",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="release",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="releasegroup",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="releaseingroup",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="releaserole",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="releasetrack",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="track",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("prefetch_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="trackrole",
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
            model_name="audiobook",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="audiobooks_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="audiobook",
            name="publisher",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="audiobooks",
                to="entity.company",
            ),
        ),
        migrations.AlterField(
            model_name="audiobook",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="audiobooks_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="audiobookinstance",
            name="audiobook",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="listen.audiobook"
            ),
        ),
        migrations.AlterField(
            model_name="audiobookinstance",
            name="instance",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="read.instance",
            ),
        ),
        migrations.AlterField(
            model_name="audiobookrole",
            name="audiobook",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="listen.audiobook"
            ),
        ),
        migrations.AlterField(
            model_name="audiobookrole",
            name="creator",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_query_name="book_roles",
                to="entity.creator",
            ),
        ),
        migrations.AlterField(
            model_name="audiobookrole",
            name="role",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="entity.role",
            ),
        ),
        migrations.AlterField(
            model_name="historicalaudiobook",
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
            model_name="historicalaudiobook",
            name="publisher",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="entity.company",
            ),
        ),
        migrations.AlterField(
            model_name="historicalaudiobook",
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
            model_name="historicalaudiobookrole",
            name="audiobook",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="listen.audiobook",
            ),
        ),
        migrations.AlterField(
            model_name="historicalaudiobookrole",
            name="creator",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                related_query_name="book_roles",
                to="entity.creator",
            ),
        ),
        migrations.AlterField(
            model_name="historicalaudiobookrole",
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
            model_name="historicalrelease",
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
            model_name="historicalrelease",
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
            model_name="historicalreleasegroup",
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
            model_name="historicalreleasegroup",
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
            model_name="historicalreleaserole",
            name="creator",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                related_query_name="release_roles",
                to="entity.creator",
            ),
        ),
        migrations.AlterField(
            model_name="historicalreleaserole",
            name="release",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="listen.release",
            ),
        ),
        migrations.AlterField(
            model_name="historicalreleaserole",
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
            model_name="historicalreleasetrack",
            name="release",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="listen.release",
            ),
        ),
        migrations.AlterField(
            model_name="historicalreleasetrack",
            name="track",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="listen.track",
            ),
        ),
        migrations.AlterField(
            model_name="historicaltrack",
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
            model_name="historicaltrack",
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
            model_name="historicaltrack",
            name="work",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="listen.work",
            ),
        ),
        migrations.AlterField(
            model_name="historicalworkrole",
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
            model_name="historicalworkrole",
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
            model_name="historicalworkrole",
            name="work",
            field=auto_prefetch.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="listen.work",
            ),
        ),
        migrations.AlterField(
            model_name="listencheckin",
            name="content_type",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AlterField(
            model_name="listencheckin",
            name="user",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AlterField(
            model_name="release",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="releases_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="release",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="releases_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="releasegroup",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="releasegroup_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="releasegroup",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="releasegroup_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="releaseingroup",
            name="group",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="listen.releasegroup"
            ),
        ),
        migrations.AlterField(
            model_name="releaseingroup",
            name="release",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="listen.release"
            ),
        ),
        migrations.AlterField(
            model_name="releaserole",
            name="creator",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_query_name="release_roles",
                to="entity.creator",
            ),
        ),
        migrations.AlterField(
            model_name="releaserole",
            name="release",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="listen.release"
            ),
        ),
        migrations.AlterField(
            model_name="releaserole",
            name="role",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="entity.role",
            ),
        ),
        migrations.AlterField(
            model_name="releasetrack",
            name="release",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="listen.release"
            ),
        ),
        migrations.AlterField(
            model_name="releasetrack",
            name="track",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="listen.track",
            ),
        ),
        migrations.AlterField(
            model_name="track",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tracks_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="track",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tracks_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="track",
            name="work",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tracks",
                to="listen.work",
            ),
        ),
        migrations.AlterField(
            model_name="trackrole",
            name="creator",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="entity.creator",
            ),
        ),
        migrations.AlterField(
            model_name="trackrole",
            name="role",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="entity.role",
            ),
        ),
        migrations.AlterField(
            model_name="trackrole",
            name="track",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="listen.track"
            ),
        ),
        migrations.AlterField(
            model_name="workrole",
            name="creator",
            field=auto_prefetch.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="listen_workrole_set",
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
                related_name="listen_workrole_set",
                to="entity.role",
            ),
        ),
        migrations.AlterField(
            model_name="workrole",
            name="work",
            field=auto_prefetch.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="listen.work"
            ),
        ),
    ]
