# Generated by Django 4.2.2 on 2023-07-13 12:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("read", "0015_alter_work_work_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="work",
            name="work_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("NO", "Novel"),
                    ("NV", "Novella"),
                    ("SS", "Short Story"),
                    ("PO", "Poem"),
                    ("ES", "Essay"),
                    ("PL", "Play"),
                    ("SC", "Screenplay"),
                    ("ME", "Memoir"),
                    ("AU", "Autobiography"),
                    ("NF", "Nonfiction"),
                    ("OT", "Other"),
                ],
                max_length=255,
                null=True,
            ),
        ),
    ]
