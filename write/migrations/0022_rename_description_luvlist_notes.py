# Generated by Django 4.2.2 on 2023-10-16 07:21

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("write", "0021_luvlist_tags"),
    ]

    operations = [
        migrations.RenameField(
            model_name="luvlist",
            old_name="description",
            new_name="notes",
        ),
    ]
