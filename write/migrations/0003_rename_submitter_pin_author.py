# Generated by Django 4.1.7 on 2023-06-12 11:15

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("write", "0002_pin"),
    ]

    operations = [
        migrations.RenameField(
            model_name="pin",
            old_name="submitter",
            new_name="author",
        ),
    ]