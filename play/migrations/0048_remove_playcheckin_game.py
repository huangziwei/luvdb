# Generated by Django 4.2.2 on 2023-11-21 21:02

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("play", "0047_migration_playcheckin_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="playcheckin",
            name="game",
        ),
    ]