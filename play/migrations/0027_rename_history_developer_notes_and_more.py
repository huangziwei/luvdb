# Generated by Django 4.2.2 on 2023-09-13 09:45

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("play", "0026_rename_description_game_notes"),
    ]

    operations = [
        migrations.RenameField(
            model_name="developer",
            old_name="history",
            new_name="notes",
        ),
        migrations.RenameField(
            model_name="gamepublisher",
            old_name="history",
            new_name="notes",
        ),
        migrations.RenameField(
            model_name="platform",
            old_name="history",
            new_name="notes",
        ),
    ]