# Generated by Django 4.2.2 on 2023-06-23 13:23

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("play", "0003_rename_subtitle_game_romanized_title"),
    ]

    operations = [
        migrations.RenameField(
            model_name="game",
            old_name="developer",
            new_name="developers",
        ),
    ]
