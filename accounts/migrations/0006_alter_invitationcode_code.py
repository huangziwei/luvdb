# Generated by Django 4.1.7 on 2023-06-10 12:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_customuser_invited_by_invitationcode_generated_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invitationcode",
            name="code",
            field=models.CharField(default="yaKk2TIp", max_length=100, unique=True),
        ),
    ]
