# Generated by Django 4.2.2 on 2023-06-28 18:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("play", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="game",
            name="cover_sens",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
