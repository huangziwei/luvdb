# Generated by Django 4.2.2 on 2023-06-09 12:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_customuser_display_name_alter_invitationcode_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invitationcode",
            name="code",
            field=models.CharField(default="HUcUqK3v", max_length=100, unique=True),
        ),
    ]
