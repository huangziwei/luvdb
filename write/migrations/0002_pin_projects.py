# Generated by Django 5.0 on 2023-12-27 12:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("write", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pin",
            name="projects",
            field=models.ManyToManyField(blank=True, to="write.project"),
        ),
    ]
