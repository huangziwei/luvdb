import random
import string

from django.db import migrations


def generate_anchor():
    # Duplicated logic from your models.py for generating a 4-character anchor
    return "".join(random.choices(string.ascii_letters + string.digits, k=4))


def generate_anchors_for_comments(apps, schema_editor):
    Comment = apps.get_model("write", "Comment")
    for comment in Comment.objects.filter(anchor=""):
        comment.anchor = generate_anchor()  # Directly set the anchor
        comment.save(update_fields=["anchor"])  # Save only the anchor field


class Migration(migrations.Migration):
    dependencies = [
        ("write", "0024_comment_anchor"),
    ]

    operations = [
        migrations.RunPython(generate_anchors_for_comments),
    ]
