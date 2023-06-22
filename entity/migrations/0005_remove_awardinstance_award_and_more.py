# Generated by Django 4.2.2 on 2023-06-21 12:58

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("entity", "0004_award_awardcategory_awardinstance_award_categories_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="awardinstance",
            name="award",
        ),
        migrations.RemoveField(
            model_name="awardinstance",
            name="category",
        ),
        migrations.RemoveField(
            model_name="awardinstance",
            name="content_type",
        ),
        migrations.DeleteModel(
            name="Award",
        ),
        migrations.DeleteModel(
            name="AwardCategory",
        ),
        migrations.DeleteModel(
            name="AwardInstance",
        ),
    ]