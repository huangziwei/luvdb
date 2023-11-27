from django.db import migrations


def associate_user_to_projects(apps, schema_editor):
    Project = apps.get_model("write", "Project")
    for project in Project.objects.all():
        # Assuming each project has at least one post
        first_post = project.post_set.first()
        if first_post:
            project.user = first_post.user
            project.save()


class Migration(migrations.Migration):
    dependencies = [
        ("write", "0034_project_user"),
    ]

    operations = [
        migrations.RunPython(associate_user_to_projects),
    ]
