# Generated by Django 5.0 on 2023-12-24 18:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_customuser_deactivated_at_customuser_is_deactivated"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebMention",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("source", models.URLField(max_length=2048)),
                ("target", models.URLField(max_length=2048)),
                ("verified", models.BooleanField(default=False)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
