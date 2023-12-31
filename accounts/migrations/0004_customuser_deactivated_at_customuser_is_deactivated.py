# Generated by Django 5.0 on 2023-12-18 16:23

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_customuser_enable_replies_by_default_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="deactivated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="customuser",
            name="is_deactivated",
            field=models.BooleanField(default=False),
        ),
    ]
