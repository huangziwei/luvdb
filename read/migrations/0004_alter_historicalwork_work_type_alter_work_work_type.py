# Generated by Django 5.0 on 2023-12-11 16:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("read", "0003_delete_historicalinstancerole"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalwork",
            name="work_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("NO", "Novel"),
                    ("NV", "Novella"),
                    ("NT", "Novelette"),
                    ("SS", "Short Story"),
                    ("PM", "Poem"),
                    ("PL", "Play"),
                    ("SC", "Script"),
                    ("MG", "Manga"),
                    ("CM", "Comic"),
                    ("CL", "Children's"),
                    ("FL", "Folktale"),
                    ("NF", "Nonfiction"),
                    ("ES", "Essay"),
                    ("TB", "Textbook"),
                    ("GU", "Guidebook"),
                    ("AR", "Article"),
                    ("SH", "Speech"),
                    ("LG", "Lecture"),
                    ("IN", "Interview"),
                    ("RE", "Review"),
                    ("LT", "Letter"),
                    ("RP", "Research Paper"),
                    ("TS", "Thesis"),
                    ("DS", "Dissertation"),
                    ("OT", "Other"),
                ],
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="work",
            name="work_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("NO", "Novel"),
                    ("NV", "Novella"),
                    ("NT", "Novelette"),
                    ("SS", "Short Story"),
                    ("PM", "Poem"),
                    ("PL", "Play"),
                    ("SC", "Script"),
                    ("MG", "Manga"),
                    ("CM", "Comic"),
                    ("CL", "Children's"),
                    ("FL", "Folktale"),
                    ("NF", "Nonfiction"),
                    ("ES", "Essay"),
                    ("TB", "Textbook"),
                    ("GU", "Guidebook"),
                    ("AR", "Article"),
                    ("SH", "Speech"),
                    ("LG", "Lecture"),
                    ("IN", "Interview"),
                    ("RE", "Review"),
                    ("LT", "Letter"),
                    ("RP", "Research Paper"),
                    ("TS", "Thesis"),
                    ("DS", "Dissertation"),
                    ("OT", "Other"),
                ],
                max_length=255,
                null=True,
            ),
        ),
    ]
