# Generated by Django 4.2.2 on 2023-10-18 14:33

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("play", "0038_rename_persons_game_creators_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="gamepublisher",
            name="created_by",
        ),
        migrations.RemoveField(
            model_name="gamepublisher",
            name="updated_by",
        ),
        migrations.DeleteModel(
            name="Developer",
        ),
        migrations.DeleteModel(
            name="GamePublisher",
        ),
    ]