# Generated by Django 4.2.2 on 2023-09-16 09:27

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("play", "0029_platform_wikipedia_alter_platform_website"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="game",
            name="developers",
        ),
        migrations.RemoveField(
            model_name="game",
            name="publishers",
        ),
        migrations.RemoveField(
            model_name="work",
            name="developers",
        ),
    ]
