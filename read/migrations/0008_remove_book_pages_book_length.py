# Generated by Django 4.2.2 on 2023-07-04 19:29

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("read", "0007_alter_work_persons_alter_workrole_person_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="book",
            name="pages",
        ),
        migrations.AddField(
            model_name="book",
            name="length",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]