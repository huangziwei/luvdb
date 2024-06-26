# Generated by Django 5.0.1 on 2024-06-18 12:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("write", "0009_album_cover_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="say",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("PU", "Public"),
                    ("ME", "Mentioned People Only"),
                    ("FO", "Followers Only"),
                    ("MF", "Mutual Friends Only"),
                    ("PR", "Private"),
                ],
                default="PU",
                max_length=2,
            ),
        ),
    ]
