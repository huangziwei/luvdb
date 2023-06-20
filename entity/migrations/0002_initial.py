# Generated by Django 4.2.2 on 2023-06-20 11:58

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("listen", "0001_initial"),
        ("read", "0001_initial"),
        ("entity", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="awardrecipient",
            name="book",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="read.book"
            ),
        ),
        migrations.AddField(
            model_name="awardrecipient",
            name="person",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="entity.person"
            ),
        ),
        migrations.AddField(
            model_name="awardrecipient",
            name="release",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="listen.release"
            ),
        ),
        migrations.AddField(
            model_name="awardrecipient",
            name="track",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="listen.track"
            ),
        ),
        migrations.AddField(
            model_name="awardrecipient",
            name="work",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="read.work"
            ),
        ),
        migrations.AddField(
            model_name="award",
            name="content_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AddField(
            model_name="award",
            name="created_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="award",
            name="updated_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="award",
            unique_together={("name", "content_type", "object_id")},
        ),
    ]
