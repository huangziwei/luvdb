# Generated by Django 4.2.2 on 2023-11-13 20:17

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("write", "0026_alter_comment_anchor"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="comment",
            name="tags",
        ),
    ]