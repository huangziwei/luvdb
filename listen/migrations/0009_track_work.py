# Generated by Django 4.2.2 on 2023-06-30 10:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0008_release_romanized_title_work_romanized_title_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="track",
            name="work",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tracks",
                to="listen.work",
            ),
        ),
    ]