# Generated by Django 4.2.2 on 2023-07-31 13:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0022_release_kkbox_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="listencheckin",
            name="status",
            field=models.CharField(
                choices=[
                    ("to_listen", "To Listen"),
                    ("looping", "Looping"),
                    ("listened", "Listened"),
                    ("paused", "Paused"),
                    ("abandoned", "Abandoned"),
                    ("afterthought", "Afterthought"),
                ],
                max_length=255,
            ),
        ),
    ]
