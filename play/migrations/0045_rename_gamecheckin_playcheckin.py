# Generated by Django 4.2.2 on 2023-11-21 19:46

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("write", "0030_alter_luvlist_order_preference"),
        ("play", "0044_gamecheckin_updated_at"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="GameCheckIn",
            new_name="PlayCheckIn",
        ),
    ]
