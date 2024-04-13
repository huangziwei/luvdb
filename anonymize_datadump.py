import argparse
import json
import os

import django
from django.apps import apps
from django.contrib.auth.hashers import make_password

# Initialize Django to use functionalities like make_password
django.setup()


def anonymize_custom_user(user_data):
    fields = {
        "password": make_password("anonymous"),
        "username": "anonymous",
        "is_superuser": True,
        "is_staff": True,
        "is_active": True,
        "email": "",
        "first_name": "",
        "last_name": "",
        "date_joined": "2023-01-01T00:00:00Z",
        "last_login": "2023-01-01T00:00:00Z",
        "bio": "",
        "is_public": False,
        "timezone": "UTC",
        "pure_text_mode": False,
        "custom_domain": "",
        "enable_replies_by_default": True,
        "enable_share_to_feed_by_default": True,
        "is_deactivated": False,
    }
    user_data["fields"].update(fields)
    return user_data


def remove_content_type_entries(data, remove_models):
    return [
        entry
        for entry in data
        if not (
            entry.get("model") == "contenttypes.contenttype"
            and entry.get("fields", {}).get("model")
            in [model.split(".")[-1] for model in remove_models]
        )
    ]


def main(file_path):
    remove_models = [
        "auth.permission",
        "accounts.invitationcode",
        "accounts.invitationrequest",
        "accounts.customuser",
        "accounts.apppassword",
        "accounts.webmention",
        "accounts.webauthncredential",
        "contenttypes.contenttype",
        "admin.logentry",
        "sessions.session",
        "read.readcheckin",
        "watch.watchcheckin",
        "listen.listencheckin",
        "play.playcheckin",
        "visit.visitcheckin",
        "notify.notification",
        "activity_feed.activity",
        "activity_feed.follow",
        "activity_feed.block",
        "discover.vote",
        "pages.page",
    ]

    # Get all models from the 'write' app
    write_app_models = apps.get_app_config("write").get_models()

    # Add the models from the 'write' app to the remove_models list
    for model in write_app_models:
        model_name = f"write.{model.__name__.lower()}"
        remove_models.append(model_name)

    with open(file_path, "r") as f:
        data = json.load(f)

    data = remove_content_type_entries(data, remove_models)

    postprocessed_data = [
        entry
        for entry in data
        if entry.get("model", "") not in remove_models
        and "historical" not in entry.get("model", "")
    ]

    for entry in postprocessed_data:
        fields = entry.get("fields", {})
        if "cover" in fields:
            fields["cover"] = None
        if "poster" in fields:
            fields["poster"] = None
        if "created_by" in fields:
            fields["created_by"] = 1
        if "updated_by" in fields:
            fields["updated_by"] = 1

    new_admin = {"model": "accounts.customuser", "pk": 1, "fields": {}}
    new_admin = anonymize_custom_user(new_admin)
    postprocessed_data.append(new_admin)

    output_file_path = os.path.join(
        os.path.dirname(file_path), "datadump_anonymized.json"
    )
    with open(output_file_path, "w") as f:
        json.dump(postprocessed_data, f, separators=(",", ":"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Anonymize a Django datadump.")
    parser.add_argument("file_path", help="The path to the JSON datadump file")
    args = parser.parse_args()
    main(args.file_path)
