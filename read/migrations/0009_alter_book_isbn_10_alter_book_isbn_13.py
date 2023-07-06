# Generated by Django 4.2.2 on 2023-07-04 19:30

from django.db import migrations
import read.models


class Migration(migrations.Migration):
    dependencies = [
        ("read", "0008_remove_book_pages_book_length"),
    ]

    operations = [
        migrations.AlterField(
            model_name="book",
            name="isbn_10",
            field=read.models.ISBNField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name="book",
            name="isbn_13",
            field=read.models.ISBNField(blank=True, max_length=13, null=True),
        ),
    ]