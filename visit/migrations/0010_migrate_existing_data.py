from django.db import migrations


def map_old_levels_to_new(apps, schema_editor):
    Location = apps.get_model("visit", "Location")
    for location in Location.objects.all():
        if location.level == "continent":
            location.level = "level0"
            location.level_name = "Continent"
        elif location.level == "polity":
            location.level = "level1"
            location.level_name = "Polity"
        elif location.level == "region":
            location.level = "level2"
            location.level_name = "State / Province / Region / Prefecture / Canton"
        elif location.level == "city":
            location.level = "level3"
            location.level_name = "County / Prefecture-level City"
        elif location.level == "town":
            location.level = "level4"
            location.level_name = "Town / Township / County-level City"
        elif location.level == "village":
            location.level = "level4"
            location.level_name = "Village / hamlet"
        elif location.level == "district":
            location.level = "level5"
            location.level_name = "District / Borough / Ward / Neighborhood"
        elif location.level == "poi":
            location.level = "level6"
            location.level_name = "Point of Interest"
        location.save()


class Migration(migrations.Migration):
    dependencies = [
        ("visit", "0009_historicallocation_level_name_location_level_name_and_more"),
    ]

    operations = [
        migrations.RunPython(map_old_levels_to_new),
    ]
