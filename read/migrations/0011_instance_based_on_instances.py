# Generated by Django 5.0.1 on 2024-05-27 16:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("read", "0010_work_mentioned_books_work_mentioned_games_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="instance",
            name="based_on_instances",
            field=models.ManyToManyField(
                blank=True, related_name="related_instances", to="read.instance"
            ),
        ),
    ]
