# Generated by Django 4.2.2 on 2023-06-18 22:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("write", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="title",
            field=models.CharField(max_length=200),
        ),
    ]
