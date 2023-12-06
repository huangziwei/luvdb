import base64
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

import auto_prefetch
import markdown
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.safestring import mark_safe


class Activity(auto_prefetch.Model):
    user = auto_prefetch.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=100, default="default_value")
    timestamp = models.DateTimeField(auto_now_add=True)

    # These fields are for the object that the activity is related to.
    # For example, if the activity is a post, the object_id would be the id of the post.
    content_type = auto_prefetch.ForeignKey(ContentType, on_delete=models.CASCADE)
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
                # settings.ROOT_URL + "/@" + self.user.username + "/followers"
                follower_url
            ]
            activitypub_message["object"]["cc"] = [
                # settings.ROOT_URL + "/@" + self.user.username + "/followers"
                follower_url
            ]
            success = sign_and_send(
                activitypub_message,
                "/@" + self.user.username + "/",
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
        actor = settings.ROOT_URL + f"/@{self.user.username}/"
        url = settings.ROOT_URL + self.content_object.get_absolute_url()

        # Content handling
        content = ""
        print(self.activity_type)
        if self.activity_type == "say":
            content = self.content_object.content + f"\n[{url}]({url})"
        elif self.activity_type == "repost":
            content = self.content_object.content + f"\n[{url}]({url})"
        elif self.activity_type == "post":
            content = f'I posted "{self.content_object.title}"' + f"\n[{url}]({url})"
        elif self.activity_type == "pin":
            content = (
                "I Pinned "
                + f'"{self.content_object.title}"'
                + f" (from [{urlparse(self.content_object.url).netloc}]({self.content_object.url}))"
                + self.content_object.content
                + f"\n[{url}]({url})"
            )
        elif "check-in" in self.activity_type:
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
                "content": mark_safe(
                    markdown.markdown(content, extensions=["pymdownx.saneheaders"])
                ),
                "contentMap": {
                    "en": mark_safe(
                        markdown.markdown(content, extensions=["pymdownx.saneheaders"])
                    )
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
                "tag": [tag.name for tag in self.content_object.tags.all()],
            },
            "published": self.timestamp.isoformat() + "Z",
        }

        if ap_activity_type in ["Update", "Delete"]:
            activity["object"]["updated"] = (
                self.content_object.updated_at.isoformat() + "Z"
            )
            if ap_activity_type == "Delete":
                activity["object"]["type"] = "Tombstone"
                activity["object"]["deleted"] = (
                    datetime.now(timezone.utc).isoformat() + "Z"
                )

        private_key = import_private_key(self.user.username)
        message = json.dumps(activity, sort_keys=True).encode()
        signature = private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )

        # Add the signature to the activity JSON
        activity["signature"] = {
            "type": "RsaSignature2017",
            "creator": actor,  # URL of the actor's public key
            "created": datetime.now(timezone.utc).isoformat() + "Z",
            "signatureValue": base64.b64encode(signature).decode(),
        }

        return activity


class Follow(auto_prefetch.Model):
    follower = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="following",
        related_query_name="following",
        on_delete=models.CASCADE,
    )
    followed = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="followers", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta(auto_prefetch.Model.Meta):
        unique_together = ("follower", "followed")


class Block(auto_prefetch.Model):
    blocker = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="blocking",
        on_delete=models.CASCADE,
    )
    blocked = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="blocked_by",
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta(auto_prefetch.Model.Meta):
        unique_together = ("blocker", "blocked")
