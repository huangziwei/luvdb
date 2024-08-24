from django.db import migrations


def copy_series_to_season(apps, schema_editor):
    Series = apps.get_model("watch", "Series")
    Season = apps.get_model("watch", "Season")
    SeriesRole = apps.get_model("watch", "SeriesRole")
    SeasonRole = apps.get_model("watch", "SeasonRole")

    for series in Series.objects.all():
        season = Season.objects.create(
            series=series,
            title=f"{series.title} Season 1",
            season_number=1,  # Assuming all are Season 1
            season_label="Season",
            subtitle=series.subtitle,
            other_titles=series.other_titles,
            release_date=series.release_date,
            notes=series.notes,
            website=series.website,
            poster=series.poster,
            poster_sens=series.poster_sens,
            duration=series.duration,
            languages=series.languages,
            status=series.status,
            imdb=series.imdb,
            wikipedia=series.wikipedia,
            official_website=series.official_website,
            created_by=series.created_by,
            updated_by=series.updated_by,
        )

        # Copy ManyToMany fields
        season.studios.set(series.studios.all())
        season.distributors.set(series.distributors.all())
        season.stars.set(series.stars.all())
        season.genres.set(series.genres.all())
        season.based_on_games.set(series.based_on_games.all())
        season.based_on_litworks.set(series.based_on_litworks.all())
        season.based_on_movies.set(series.based_on_movies.all())
        season.based_on_series.set(series.based_on_series.all())
        season.soundtracks.set(series.soundtracks.all())

        # Copy SeriesRole to SeasonRole
        for series_role in SeriesRole.objects.filter(series=series):
            SeasonRole.objects.create(
                season=season,
                creator=series_role.creator,
                role=series_role.role,
                alt_name=series_role.alt_name,
            )

        season.save()


class Migration(migrations.Migration):

    dependencies = [
        ("watch", "0021_historicalseason_season_historicalseasonrole_and_more"),
    ]

    operations = [
        migrations.RunPython(copy_series_to_season),
    ]
