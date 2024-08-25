from django.db import migrations


def populate_season_field(apps, schema_editor):
    Episode = apps.get_model("watch", "Episode")
    Season = apps.get_model("watch", "Season")

    for episode in Episode.objects.all():
        try:
            # Find the Season object using the series and season_number
            season = Season.objects.get(
                series=episode.series, season_number=episode.season.season_number
            )
            # Assign the Season object to the season foreign key
            episode.season = season
            episode.save()
        except Season.DoesNotExist:
            print(f"Season does not exist for Episode {episode.id}")


class Migration(migrations.Migration):

    dependencies = [
        (
            "watch",
            "0023_alter_episode_season_alter_historicalepisode_season",
        ),
    ]

    operations = [
        migrations.RunPython(populate_season_field),
    ]
