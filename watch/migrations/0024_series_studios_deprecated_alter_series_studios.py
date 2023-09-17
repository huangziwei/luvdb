# Generated by Django 4.2.2 on 2023-09-16 13:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("entity", "0011_company"),
        ("watch", "0023_movie_studios_deprecated_alter_movie_studios"),
    ]

    operations = [
        migrations.AddField(
            model_name="series",
            name="studios_deprecated",
            field=models.ManyToManyField(related_name="series", to="watch.studio"),
        ),
        migrations.AlterField(
            model_name="series",
            name="studios",
            field=models.ManyToManyField(related_name="series", to="entity.company"),
        ),
    ]