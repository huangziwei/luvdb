# Generated by Django 4.2.2 on 2023-08-07 14:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("entity", "0004_person_other_names"),
    ]

    operations = [
        migrations.AlterField(
            model_name="person",
            name="other_names",
            field=models.TextField(blank=True, max_length=200, null=True),
        ),
    ]