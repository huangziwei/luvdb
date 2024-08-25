from django.contrib.contenttypes.models import ContentType
from django.db import migrations
from django.utils.timezone import now

from watch.models import WatchCheckIn


def create_content_type(apps, schema_editor):
    # Ensure ContentType exists for Season and Series
    ContentType.objects.get_or_create(app_label="watch", model="series")
    ContentType.objects.get_or_create(app_label="watch", model="season")


def copy_series_to_season(apps, schema_editor):
    Series = apps.get_model("watch", "Series")
    Season = apps.get_model("watch", "Season")
    SeriesRole = apps.get_model("watch", "SeriesRole")
    SeasonRole = apps.get_model("watch", "SeasonRole")
    HistoricalSeries = apps.get_model("watch", "HistoricalSeries")
    HistoricalSeason = apps.get_model("watch", "HistoricalSeason")

    WatchCheckIn = apps.get_model("watch", "WatchCheckIn")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Ensure ContentType exists
    series_content_type = ContentType.objects.get(app_label="watch", model="series")
    season_content_type = ContentType.objects.get(app_label="watch", model="season")

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
            season_role = SeasonRole.objects.create(
                season=season,
                creator=series_role.creator,
                role=series_role.role,
                alt_name=series_role.alt_name,
            )

        # Copy HistoricalSeries to HistoricalSeason
        for historical_series in HistoricalSeries.objects.filter(id=series.id):
            HistoricalSeason.objects.create(
                history_date=historical_series.history_date,
                history_user=historical_series.history_user,
                history_change_reason=historical_series.history_change_reason,
                history_type=historical_series.history_type,
                id=historical_series.id,  # Or generate a new ID if needed
                series_id=series.id,  # Manually set the series_id
                title=f"{historical_series.title} Season 1",
                season_number=1,
                season_label="Season",
                subtitle=historical_series.subtitle,
                other_titles=historical_series.other_titles,
                release_date=historical_series.release_date,
                notes=historical_series.notes,
                website=historical_series.website,
                poster=historical_series.poster,
                poster_sens=historical_series.poster_sens,
                duration=historical_series.duration,
                languages=historical_series.languages,
                status=historical_series.status,
                imdb=historical_series.imdb,
                wikipedia=historical_series.wikipedia,
                official_website=historical_series.official_website,
                created_by=historical_series.created_by,
                updated_by=historical_series.updated_by,
                created_at=historical_series.history_date,  # Use history_date for created_at
                updated_at=historical_series.history_date,  # Use history_date for updated_at
            )

        # Migrate existing WatchCheckIn from Series to Season
        WatchCheckIn.objects.filter(
            content_type=series_content_type, object_id=series.id
        ).update(
            content_type=season_content_type,
            object_id=season.id,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("watch", "0021_historicalseason_season_historicalseasonrole_and_more"),
    ]

    operations = [
        migrations.RunPython(create_content_type),
        migrations.RunPython(copy_series_to_season),
    ]
