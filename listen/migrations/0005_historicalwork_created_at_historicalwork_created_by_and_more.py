# Generated by Django 5.0 on 2023-12-28 16:50

import auto_prefetch
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0004_alter_listencheckin_progress_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalwork",
            name="created_at",
            field=models.DateTimeField(
                blank=True, default=django.utils.timezone.now, editable=False
            ),
            preserve_default=False,
        ),
        migrations.AddField(
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
        migrations.AddField(
            model_name="historicalwork",
            name="updated_at",
            field=models.DateTimeField(
                blank=True, default=django.utils.timezone.now, editable=False
            ),
            preserve_default=False,
        ),
        migrations.AddField(
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
        migrations.AddField(
            model_name="work",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="work",
            name="created_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="musicwork_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="work",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="work",
            name="updated_by",
            field=auto_prefetch.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="musicwork_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
