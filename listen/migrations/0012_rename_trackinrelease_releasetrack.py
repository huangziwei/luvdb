# Generated by Django 4.2.2 on 2023-06-30 12:15

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0011_alter_releaserole_person_alter_releaserole_role"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="TrackInRelease",
            new_name="ReleaseTrack",
        ),
    ]