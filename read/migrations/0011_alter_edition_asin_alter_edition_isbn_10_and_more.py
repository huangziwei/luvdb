# Generated by Django 4.2.2 on 2023-06-16 10:09

from django.db import migrations, models
import read.models


class Migration(migrations.Migration):
    dependencies = [
        ("read", "0010_remove_edition_identifier_alter_edition_price"),
    ]

    operations = [
        migrations.AlterField(
            model_name="edition",
            name="asin",
            field=models.CharField(
                blank=True,
                max_length=10,
                null=True,
                validators=[read.models.validate_asin],
            ),
        ),
        migrations.AlterField(
            model_name="edition",
            name="isbn_10",
            field=models.CharField(
                blank=True,
                max_length=10,
                null=True,
                validators=[read.models.validate_isbn_10],
            ),
        ),
        migrations.AlterField(
            model_name="edition",
            name="isbn_13",
            field=models.CharField(
                blank=True,
                max_length=13,
                null=True,
                validators=[read.models.validate_isbn_13],
            ),
        ),
    ]
