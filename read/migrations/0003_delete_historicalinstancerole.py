# Generated by Django 5.0 on 2023-12-09 15:57

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("read", "0002_initial"),
    ]

    operations = [
        migrations.DeleteModel(
            name="HistoricalInstanceRole",
        ),
    ]
