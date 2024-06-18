# Generated by Django 5.0.1 on 2024-06-18 14:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activity_feed", "0002_activity_visibility"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activity",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("PU", "Public"),
                    ("ME", "Mentioned"),
                    ("FO", "Followers"),
                    ("MF", "Mutual Friends"),
                    ("PR", "Private"),
                ],
                default="PU",
                max_length=2,
            ),
        ),
    ]
