# Generated by Django 4.2.2 on 2023-10-09 12:04

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("discover", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="vote",
            name="timestamp",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
    ]