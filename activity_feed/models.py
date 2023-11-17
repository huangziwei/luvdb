from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

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
        # Call the real save method
        super(Activity, self).save(*args, **kwargs)

        if is_new:
            print("New activity created")
            print("Updating user outbox")
            self.update_user_outbox(activity_type="Create")

    def update_user_outbox(self, activity_type="Create"):
        activitypub_message = self.to_activitypub(activity_type=activity_type)
        followers = self.user.fediversefollower_set.all()
        private_key = import_private_key(self.user.username)
        for follower in followers:
            follower_url = follower.follower_uri
            target_domain = follower_url.split("/")[2]
            print(follower_url, target_domain)
            activitypub_message["cc"] = [follower_url]
            activitypub_message["object"]["cc"] = [follower_url]
            success = sign_and_send(
                activitypub_message,
                "/u/" + self.user.username + "/actor/",
                settings.ROOT_URL,
                target_domain,
                private_key,
            )
            if success:
                print("Sent to:", follower_url)
            else:
                print("Failed to send to:", follower_url)

    def to_activitypub(self, activity_type="Create"):
        actor = settings.ROOT_URL + f"/u/{self.user.username}/actor/"
        if self.activity_type == "say":
            content = self.content_object.content
            url = settings.ROOT_URL + self.content_object.get_absolute_url()

        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": url,
            "type": activity_type,
            "actor": actor,
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "object": {
                "id": url,
                "type": "Note",  # Change this depending on the content type
                "content": content,
                "to": ["https://www.w3.org/ns/activitystreams#Public"],
                "published": self.timestamp.isoformat(),
                "attributedTo": settings.ROOT_URL + self.user.get_absolute_url(),
                "inReplyTo": None,
            },
            "published": self.timestamp.isoformat(),
        }
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
