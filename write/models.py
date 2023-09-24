import json
import random
import re
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from activity_feed.models import Activity
from notify.models import Notification
from notify.views import create_mentions_notifications

User = get_user_model()


def handle_tags(instance, content):
    instance.tags.clear()
    tags = set(re.findall(r"#(\w+)", content))
    for tag in tags:
        tag_obj, created = Tag.objects.get_or_create(name=tag)
        instance.tags.add(tag_obj)


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Comment(models.Model):
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, blank=True)

    # Polymorphic relationship to Post, Say, or Pin
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return f"Comment by {self.user} on {self.content_object}"

    def get_absolute_url(self):
        return self.content_object.get_absolute_url()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.user != self.content_object.user:
            user_url = reverse("accounts:detail", args=[self.user.username])
            user_name = (
                self.user.display_name if self.user.display_name else self.user.username
            )
            content_url = self.content_object.get_absolute_url()
            content_name = self.content_object.__class__.__name__.capitalize()
            message = f'<a href="{user_url}">@{user_name}</a> commented on your <a href="{content_url}">{content_name}</a>.'

            Notification.objects.create(
                recipient=self.content_object.user,
                sender_content_type=ContentType.objects.get_for_model(self.user),
                sender_object_id=self.user.id,
                notification_type="comment",
                message=message,
            )
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


class Repost(models.Model):
    original_activity = models.ForeignKey(
        Activity, on_delete=models.SET_NULL, related_name="reposts", null=True
    )
    original_repost = models.ForeignKey(
        "self", on_delete=models.SET_NULL, related_name="reposts", null=True, blank=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    comments = GenericRelation(Comment)
    comments_enabled = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    def get_absolute_url(self):
        return reverse("write:repost_detail", args=[str(self.id)])

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="repost", object_id=self.id
            )
            return activity.id
        except ObjectDoesNotExist:
            return None

    def get_reposts(self):
        return Repost.objects.filter(original_repost=self).exclude(id=self.id)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Activity.objects.create(
                user=self.user,
                activity_type="repost",
                content_object=self,
            )

            # Create notification for repost
            if self.user != self.original_activity.user:
                user_url = reverse("accounts:detail", args=[self.user.username])
                content_url = self.original_activity.content_object.get_absolute_url()
                content_name = (
                    self.original_activity.content_object.__class__.__name__.capitalize()
                )
                if "checkin" in content_name:
                    content_name = "Check-in"

                repost_url = self.get_absolute_url()
                message = f'<a href="{user_url}">@{self.user.username}</a> reposted your <a href="{content_url}">{content_name}</a>. See the <a href="{repost_url}">Repost</a>.'

                Notification.objects.create(
                    recipient=self.original_activity.user,
                    sender_content_type=ContentType.objects.get_for_model(self.user),
                    sender_object_id=self.user.id,
                    notification_type="repost",
                    message=message,
                )

        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    comments = GenericRelation(Comment)
    comments_enabled = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, blank=True)
    reposts = GenericRelation(Repost)

    def get_absolute_url(self):
        return reverse("write:post_detail", args=[str(self.id)])

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="post", object_id=self.id
            )
            return activity.id
        except ObjectDoesNotExist:
            return None

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Activity.objects.create(
                user=self.user,
                activity_type="post",
                content_object=self,
            )
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


class Say(models.Model):
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    comments = GenericRelation(Comment)
    comments_enabled = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, blank=True)
    reposts = GenericRelation(Repost)

    def get_absolute_url(self):
        return reverse("write:say_detail", args=[str(self.id)])

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="say", object_id=self.id
            )
            return activity.id
        except ObjectDoesNotExist:
            return None

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Activity.objects.create(
                user=self.user,
                activity_type="say",
                content_object=self,
            )
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


class Pin(models.Model):
    title = models.TextField()
    url = models.URLField()
    content = models.TextField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    comments = GenericRelation(Comment)
    comments_enabled = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, blank=True)
    reposts = GenericRelation(Repost)

    def get_absolute_url(self):
        return reverse("write:pin_detail", args=[str(self.id)])

    def get_activity_id(self):
        try:
            activity = Activity.objects.get(
                content_type__model="pin", object_id=self.id
            )
            return activity.id
        except ObjectDoesNotExist:
            return None

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Activity.objects.create(
                user=self.user,
                activity_type="pin",
                content_object=self,
            )
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.user, self.content, self)


# delete activity when a `write` is deleted
@receiver(post_delete, sender=Post)
@receiver(post_delete, sender=Say)
@receiver(post_delete, sender=Pin)
@receiver(post_delete, sender=Repost)
@receiver(post_delete, sender="read.ReadCheckIn")
@receiver(post_delete, sender="listen.ListenCheckIn")
@receiver(post_delete, sender="watch.WatchCheckIn")
@receiver(post_delete, sender="play.GameCheckIn")
@receiver(post_delete, sender="activity_feed.Follow")
def delete_activity(sender, instance, **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    Activity.objects.filter(content_type=content_type, object_id=instance.id).delete()


# notify comment users when a `write` is deleted
@receiver(pre_delete, sender=Post)
@receiver(pre_delete, sender=Say)
@receiver(pre_delete, sender=Pin)
@receiver(pre_delete, sender=Repost)
@receiver(pre_delete, sender="read.ReadCheckIn")
@receiver(pre_delete, sender="listen.ListenCheckIn")
@receiver(pre_delete, sender="watch.WatchCheckIn")
@receiver(pre_delete, sender="play.GameCheckIn")
def notify_comment_users(sender, instance, **kwargs):
    # Get all the comments on the object being deleted
    comments = instance.comments.all()

    # For each comment, create a notification for the user
    for comment in comments:
        # Check if the user of the comment is the same as the user of the object
        if comment.user == instance.user:
            # If they are the same, return early and do not create a notification
            continue

        # Create a message for the notification
        message = f"A {sender.__name__} your commented was deleted, thus your comment was also deleted: <br><blockquote>{comment.content}</blockquote>"

        # Create the notification
        Notification.objects.create(
            recipient=comment.user,
            sender_content_type=ContentType.objects.get_for_model(instance.user),
            sender_object_id=instance.user.id,
            notification_type="comment_on_deleted",
            message=message,
        )


# notify comment user when comment is deleted by parent user
@receiver(pre_delete, sender=Comment)
def notify_comment_user_on_deletion(sender, instance, **kwargs):
    # Delay the execution of the following code until after the current transaction is committed
    def _notify_comment_user_on_deletion():
        # Check if the content_object of the comment is being deleted
        if (
            instance.content_object is not None
            and instance.content_object.pk is not None
        ):
            # If the content_object is not being deleted, check if the user of the comment is not the same as the user of the object
            if instance.user != instance.content_object.user:
                # Create a message for the notification
                content_url = instance.content_object.get_absolute_url()
                message = f"Your comment on a <a href={content_url}>{instance.content_object.__class__.__name__}</a> was deleted by the user: <br><blockquote>{instance.content}</blockquote>"

                # Create the notification
                Notification.objects.create(
                    recipient=instance.user,
                    sender_content_type=ContentType.objects.get_for_model(
                        instance.content_object.user
                    ),
                    sender_object_id=instance.content_object.user.id,
                    notification_type="comment_deleted_by_user",
                    message=message,
                )

    transaction.on_commit(_notify_comment_user_on_deletion)


# delete repost when activity is deleted
@receiver(post_delete, sender=Activity)
def delete_repost(sender, instance, **kwargs):
    # Check if the associated object is a Repost
    if isinstance(instance.content_object, Repost):
        # Delete the Repost object
        instance.content_object.delete()


# delete say when activity is deleted
@receiver(post_delete, sender=Activity)
def delete_say(sender, instance, **kwargs):
    # Check if the associated object is a Repost
    if isinstance(instance.content_object, Say):
        # Delete the Repost object
        instance.content_object.delete()


class LuvList(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    user = models.ForeignKey(
        User,
        related_name="luvlists_created",
        on_delete=models.SET_NULL,
        null=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("write:luvlist_detail", args=[str(self.id)])


class ContentInList(models.Model):
    luv_list = models.ForeignKey(
        LuvList, related_name="contents", on_delete=models.CASCADE
    )
    order = models.PositiveIntegerField(null=True, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    comment = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.luv_list.title}: {self.content_object}"


class Randomizer(models.Model):
    luv_list = models.ForeignKey(
        LuvList, related_name="randomizers", on_delete=models.CASCADE
    )
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    last_generated_item = models.ForeignKey(
        ContentInList,
        related_name="randomized_in",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    last_generated_datetime = models.DateTimeField(
        null=True, blank=True
    )  # Changed from DateField to DateTimeField
    randomized_order = models.TextField(null=True, blank=True)
    interval_in_seconds = models.IntegerField(
        default=86400
    )  # New field for interval in seconds

    @classmethod
    def get_randomizer(cls, luv_list, user=None):
        return cls.objects.get_or_create(luv_list=luv_list, user=user)[0]

    def generate_item(self):
        now = timezone.now()

        if (
            self.last_generated_datetime
            and (now - self.last_generated_datetime).total_seconds()
            < self.interval_in_seconds
        ):
            return self.last_generated_item

        current_items = list(self.luv_list.contents.all())
        current_item_ids = {item.id for item in current_items}

        if not self.randomized_order:
            random_order = [
                item.id for item in random.sample(current_items, len(current_items))
            ]
        else:
            random_order = json.loads(self.randomized_order)
            random_order = [
                item_id for item_id in random_order if item_id in current_item_ids
            ]
            new_item_ids = current_item_ids - set(random_order)
            random_order.extend(random.sample(list(new_item_ids), len(new_item_ids)))

        if not random_order:
            random_order = [
                item.id for item in random.sample(current_items, len(current_items))
            ]

        next_item_id = random_order.pop(0)
        next_item = ContentInList.objects.get(id=next_item_id)

        self.last_generated_item = next_item
        self.last_generated_datetime = now  # Update to use DateTime
        self.randomized_order = json.dumps(random_order if random_order else None)

        self.save()
        return next_item
