# Generated by Django 4.2.2 on 2023-08-24 10:27

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("play", "0023_game_rating"),
    ]

    operations = [
        migrations.AddField(
            model_name="game",
            name="wikipedia",
            field=models.URLField(blank=True, null=True),
        ),
    ]
