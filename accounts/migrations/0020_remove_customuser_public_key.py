# Generated by Django 4.2.2 on 2023-12-06 12:06

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0019_remove_customuser_enable_federation_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="customuser",
            name="public_key",
        ),
    ]