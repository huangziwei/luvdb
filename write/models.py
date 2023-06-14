import re

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

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
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, blank=True)

    # Polymorphic relationship to Post, Say, or Pin
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return f"Comment by {self.author} on {self.content_object}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.author != self.content_object.author:
            author_url = reverse("accounts:detail", args=[self.author.username])
            author_name = (
                self.author.display_name
                if self.author.display_name
                else self.author.username
            )
            content_url = self.content_object.get_absolute_url()
            content_name = self.content_object.__class__.__name__.capitalize()
            message = f'<a href="{author_url}">@{author_name}</a> commented on your <a href="{content_url}">{content_name}</a>.'

            Notification.objects.create(
                recipient=self.content_object.author,
                sender_content_type=ContentType.objects.get_for_model(self.author),
                sender_object_id=self.author.id,
                notification_type="comment",
                message=message,
            )
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.author, self.content, self)


class Repost(models.Model):
    original_activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="reposts"
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    comments = GenericRelation(Comment)
    comments_enabled = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, blank=True)

    # Polymorphic relationship to Post, Say, or Pin
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    def get_absolute_url(self):
        return reverse("write:repost_detail", args=[str(self.id)])

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Activity.objects.create(
                user=self.author,
                activity_type="repost",
                content_object=self,
            )

            # Create notification for repost
            if self.author != self.original_activity.user:
                author_url = reverse("accounts:detail", args=[self.author.username])
                content_url = self.original_activity.content_object.get_absolute_url()
                content_name = (
                    self.original_activity.content_object.__class__.__name__.capitalize()
                )
                repost_url = self.get_absolute_url()
                message = f'<a href="{author_url}">@{self.author.username}</a> reposted your <a href="{content_url}">{content_name}</a>. See the <a href="{repost_url}">Repost</a>.'

                Notification.objects.create(
                    recipient=self.original_activity.user,
                    sender_content_type=ContentType.objects.get_for_model(self.author),
                    sender_object_id=self.author.id,
                    notification_type="repost",
                    message=message,
                )

        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.author, self.content, self)


class Post(models.Model):
    title = models.CharField(max_length=200, null=True, blank=True)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
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
                user=self.author,
                activity_type="post",
                content_object=self,
            )
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.author, self.content, self)


class Say(models.Model):
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
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
                user=self.author,
                activity_type="say",
                content_object=self,
            )
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.author, self.content, self)


class Pin(models.Model):
    title = models.TextField()
    url = models.URLField()
    content = models.TextField(null=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
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
                user=self.author,
                activity_type="pin",
                content_object=self,
            )
        # Handle tags
        handle_tags(self, self.content)
        create_mentions_notifications(self.author, self.content, self)


@receiver(post_delete, sender=Post)
@receiver(post_delete, sender=Say)
@receiver(post_delete, sender=Pin)
@receiver(post_delete, sender=Repost)
def delete_activity(sender, instance, **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    Activity.objects.filter(content_type=content_type, object_id=instance.id).delete()
