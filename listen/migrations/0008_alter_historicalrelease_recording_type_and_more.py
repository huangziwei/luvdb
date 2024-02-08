# Generated by Django 5.0.1 on 2024-01-30 21:20

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0007_historicalrelease_internet_archive_url_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalrelease",
            name="recording_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("Studio", "Studio"),
                    ("Live", "Live"),
                    ("Studio and Live", "Studio and Live"),
                    ("Compilation", "Compilation"),
                    ("Bootleg", "Bootleg"),
                    ("Soundtrack", "Soundtrack"),
                ],
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="release",
            name="recording_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("Studio", "Studio"),
                    ("Live", "Live"),
                    ("Studio and Live", "Studio and Live"),
                    ("Compilation", "Compilation"),
                    ("Bootleg", "Bootleg"),
                    ("Soundtrack", "Soundtrack"),
                ],
                max_length=255,
                null=True,
            ),
        ),
    ]