# Generated by Django 4.2.2 on 2023-07-20 22:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("read", "0016_alter_work_work_type"),
        ("watch", "0007_studio_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="movie",
            name="based_on",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="movies",
                to="read.work",
            ),
        ),
        migrations.AddField(
            model_name="series",
            name="based_on",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="series",
                to="read.work",
            ),
        ),
        migrations.AlterField(
            model_name="episoderole",
            name="episode",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="episoderoles",
                to="watch.episode",
            ),
        ),
    ]