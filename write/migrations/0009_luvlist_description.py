# Generated by Django 4.2.2 on 2023-07-13 19:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("write", "0008_contentinlist_timestamp"),
    ]

    operations = [
        migrations.AddField(
            model_name="luvlist",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
    ]