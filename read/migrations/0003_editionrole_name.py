# Generated by Django 4.2.2 on 2023-06-16 08:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("read", "0002_editionrole_edition_persons"),
    ]

    operations = [
        migrations.AddField(
            model_name="editionrole",
            name="name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
