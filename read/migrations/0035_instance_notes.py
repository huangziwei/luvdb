# Generated by Django 4.2.2 on 2023-08-30 14:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("read", "0034_bookseries_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="instance",
            name="notes",
            field=models.TextField(blank=True, null=True),
        ),
    ]
