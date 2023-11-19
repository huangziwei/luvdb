from datetime import datetime
from urllib.parse import urlparse

import markdown
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.safestring import mark_safe

from accounts.utils_activitypub import import_private_key, sign_and_send


class Activity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=100, default="default_value")
    timestamp = models.DateTimeField(auto_now_add=True)

    # These fields are for the object that the activity is related to.
    # For example, if the activity is a post, the object_id would be the id of the post.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    comments = GenericRelation("write.Comment")
    reposts = GenericRelation("write.Repost")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        was_update = False
        if not is_new:
            # Retrieve the current content_object (Say instance)
            current_content_object = self.content_object
            # Compare timestamps to check for updates
            was_update = (
                current_content_object.updated_at > current_content_object.timestamp
            )

        # Call the real save method
        super(Activity, self).save(*args, **kwargs)

        if self.user.enable_federation:
            if is_new:
                print("New activity created")
                print("Updating user outbox")
                self.update_user_outbox(ap_activity_type="Create")
            elif was_update:
                print("Activity updated")
                self.update_user_outbox(ap_activity_type="Update")

    def delete(self, *args, **kwargs):
        if self.user.enable_federation:
            # Create and send DELETE ActivityPub message
            print("Deleting activity")
            self.update_user_outbox(ap_activity_type="Delete")

        # Call the real delete method
        super(Activity, self).delete(*args, **kwargs)

    def update_user_outbox(self, ap_activity_type="Create"):
        activitypub_message = self.to_activitypub(ap_activity_type=ap_activity_type)
        followers = self.user.fediversefollower_set.all()
        private_key = import_private_key(self.user.username)

        for follower in followers:
            follower_url = follower.follower_uri
            follower_shared_inbox = follower.follower_shared_inbox
            preferred_headers = follower.preferred_headers

            target_domain = follower_url.split("/")[2]
            activitypub_message["cc"] = [
                settings.ROOT_URL + "/u/" + self.user.username + "/followers"
            ]
            activitypub_message["object"]["cc"] = [
                settings.ROOT_URL + "/u/" + self.user.username + "/followers"
            ]
            success = sign_and_send(
                activitypub_message,
                "/u/" + self.user.username + "/",
                settings.ROOT_URL,
                target_domain,
                private_key,
                preferred_headers,
                inbox=follower_shared_inbox,
            )
            if success:
                print("Sent to:", follower_url)
            else:
                print("Failed to send to:", follower_url)

    def to_activitypub(self, ap_activity_type="Create"):
        actor = settings.ROOT_URL + f"/u/{self.user.username}/"
        url = settings.ROOT_URL + self.content_object.get_absolute_url()

        # Content handling
        content = ""
        print(self.activity_type)
        if self.activity_type == "say":
            content = self.content_object.content + f"\n[{url}]({url})"
        elif self.activity_type == "repost":
            content = self.content_object.content + f"\n[{url}]({url})"
        elif self.activity_type == "post":
            content = "New Post:\n" + self.content_object.title + f"\n[{url}]({url})"
        elif self.activity_type == "pin":
            content = (
                "New Pin:\n"
                + self.content_object.title
                + f"(from [{urlparse(self.content_object.url).netloc}](self.content_object.url))"
                + f"\n[{url}]({url})"
            )
        elif "game" in self.activity_type:
            content = self.content_object.content + f"\n[{url}]({url})"
        elif "check-in" in self.activity_type and "game" not in self.activity_type:
            content = self.content_object.content + f"\n[{url}]({url})"
        else:
            raise ValueError("Invalid activity type")

        # Adding additional namespaces and properties for Pleroma compatibility
        activity = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1",
            ],
            "id": url,
            "type": ap_activity_type,
            "actor": actor,
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "object": {
                "actor": actor,
                "atomUri": url,
                "attachment": [],
                "attributedTo": settings.ROOT_URL + self.user.get_absolute_url(),
                # "cc": [], # This is added later
                "content": mark_safe(markdown.markdown(content)),
                "contentMap": {"en": mark_safe(markdown.markdown(content))},
                "context": {
                    "https://www.w3.org/ns/activitystreams#partOf": {
                        "https://www.w3.org/ns/activitystreams#name": "LuvDB"
                    }
                },
                "conversation": "tag:"
                + urlparse(settings.ROOT_URL).netloc
                + ","
                + self.timestamp.strftime("%Y-%m-%d")
                + ":objectId="
                + str(self.id)
                + ":objectType=Conversation",
                "id": url,
                "inReplyTo": None,
                "published": self.timestamp.isoformat() + "Z",
                "sensitive": False,
                "source": {"content": content, "mediaType": "text/plain"},
                "summary": "",
                "type": "Note",
                "to": ["https://www.w3.org/ns/activitystreams#Public"],
                "tag": [],
            },
            "published": self.timestamp.isoformat() + "Z",
        }

        if ap_activity_type in ["Update", "Delete"]:
            activity["object"]["updated"] = (
                self.content_object.updated_at.isoformat() + "Z"
            )
            if ap_activity_type == "Delete":
                activity["object"]["type"] = "Tombstone"
                activity["object"]["deleted"] = datetime.utcnow().isoformat() + "Z"

        return activity


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="following",
        related_query_name="following",
        on_delete=models.CASCADE,
    )
    followed = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="followers", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "followed")


class Block(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="blocking",
        on_delete=models.CASCADE,
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="blocked_by",
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("blocker", "blocked")
