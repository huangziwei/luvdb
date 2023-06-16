# Generated by Django 4.2.2 on 2023-06-16 09:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("read", "0007_edition_asin_edition_isbn_10_edition_isbn_13_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="book",
            name="publication_date",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name="publisher",
            name="closed_date",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name="publisher",
            name="founded_date",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
