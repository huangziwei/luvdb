# Generated by Django 4.2.2 on 2023-08-15 07:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("watch", "0012_alter_studio_closed_date_alter_studio_founded_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="movie",
            name="wikipedia",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="series",
            name="wikipedia",
            field=models.URLField(blank=True, null=True),
        ),
    ]
