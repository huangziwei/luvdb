# Generated by Django 4.2.2 on 2023-09-13 09:45

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("read", "0035_instance_notes"),
    ]

    operations = [
        migrations.RenameField(
            model_name="publisher",
            old_name="history",
            new_name="notes",
        ),
    ]