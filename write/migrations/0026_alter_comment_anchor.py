# Generated by Django 4.2.2 on 2023-11-13 14:47

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("write", "0025_auto_20231110_1458"),
    ]

    operations = [
        migrations.AlterField(
            model_name="comment",
            name="anchor",
            field=models.CharField(blank=True, max_length=4),
        ),
    ]