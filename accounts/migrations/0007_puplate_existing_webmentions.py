from django.db import migrations

from accounts.views import fetch_bridgy_data  # Adjust the import path as needed


def update_webmentions(apps, schema_editor):
    WebMention = apps.get_model(
        "accounts", "WebMention"
    )  # Adjust app name and model name
    for webmention in WebMention.objects.all():
        try:
            author_name, author_url, content, mention_type = fetch_bridgy_data(
                webmention.source
            )
            webmention.author_name = author_name
            webmention.author_url = author_url
            webmention.content = content
            webmention.mention_type = mention_type
            webmention.save()
        except:
            pass


class Migration(migrations.Migration):
    dependencies = [
        (
            "accounts",
            "0006_webmention_author_name_webmention_author_url_and_more",
        ),  # Replace with your app's last migration
    ]

    operations = [
        migrations.RunPython(update_webmentions),
    ]
