from django.contrib.contenttypes.models import ContentType
from django.db import migrations


def migrate_game_to_generic(apps, schema_editor):
    PlayCheckIn = apps.get_model("play", "PlayCheckIn")
    Game = apps.get_model("play", "Game")
    game_content_type = ContentType.objects.get_for_model(Game)

    for checkin in PlayCheckIn.objects.all():
        if checkin.game_id is not None:
            checkin.content_type_id = game_content_type.id
            checkin.object_id = checkin.game_id
            checkin.save()


class Migration(migrations.Migration):
    dependencies = [
        ("play", "0046_playcheckin_content_type_playcheckin_object_id"),
    ]

    operations = [
        migrations.RunPython(migrate_game_to_generic),
    ]
