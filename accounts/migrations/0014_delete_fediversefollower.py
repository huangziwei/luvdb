# Generated by Django 4.2.2 on 2023-11-15 23:19

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_fediversefollower"),
    ]

    operations = [
        migrations.DeleteModel(
            name="FediverseFollower",
        ),
    ]
