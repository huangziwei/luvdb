# Generated by Django 4.2.2 on 2023-11-01 21:44

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("listen", "0066_historicalworkrole_historicalwork_historicaltrack_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="HistoricalPodcast",
        ),
    ]