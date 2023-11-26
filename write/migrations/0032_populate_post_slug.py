from django.db import migrations
from django.utils.text import slugify


def generate_slugs(apps, schema_editor):
    Post = apps.get_model("write", "Post")
    for post in Post.objects.all():
        post.slug = slugify(post.title, allow_unicode=True)
        post.save()


class Migration(migrations.Migration):
    dependencies = [
        ("write", "0031_post_slug"),
    ]

    operations = [
        migrations.RunPython(generate_slugs),
    ]
