# Generated by Django 4.2.2 on 2023-09-13 09:45

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("watch", "0020_contentincollection_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="studio",
            old_name="history",
            new_name="notes",
        ),
    ]
