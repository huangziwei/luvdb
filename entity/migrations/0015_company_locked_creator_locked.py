# Generated by Django 4.2.2 on 2023-10-30 09:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("entity", "0014_rename_closed_date_company_defunct_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="locked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="creator",
            name="locked",
            field=models.BooleanField(default=False),
        ),
    ]