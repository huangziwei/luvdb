# Generated by Django 4.2.2 on 2023-07-09 12:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0019_alter_releasetrack_disk_alter_releasetrack_order_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="label",
            name="note",
            field=models.TextField(blank=True, null=True),
        ),
    ]
