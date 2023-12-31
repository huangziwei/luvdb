# Generated by Django 5.0.1 on 2024-01-06 16:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("play", "0003_dlc_dlccast_dlc_casts_dlcrole_dlc_creators_and_more"),
        ("visit", "0012_historicallocation_osm_id_location_osm_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalwork",
            name="setting_locations_hierarchy",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="work",
            name="setting_locations",
            field=models.ManyToManyField(
                blank=True, related_name="games_set_here", to="visit.location"
            ),
        ),
        migrations.AddField(
            model_name="work",
            name="setting_locations_hierarchy",
            field=models.TextField(blank=True, null=True),
        ),
    ]
