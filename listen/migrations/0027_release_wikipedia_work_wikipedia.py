# Generated by Django 4.2.2 on 2023-08-15 07:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0026_label_wikipedia"),
    ]

    operations = [
        migrations.AddField(
            model_name="release",
            name="wikipedia",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="work",
            name="wikipedia",
            field=models.URLField(blank=True, null=True),
        ),
    ]
