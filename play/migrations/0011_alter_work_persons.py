# Generated by Django 4.2.2 on 2023-07-11 09:20

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("entity", "0002_person_note"),
        ("play", "0010_alter_work_persons"),
    ]

    operations = [
        migrations.AlterField(
            model_name="work",
            name="persons",
            field=models.ManyToManyField(
                related_name="play_works", through="play.WorkRole", to="entity.person"
            ),
        ),
    ]
