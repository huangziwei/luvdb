from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

from activity_feed.models import Activity

User = get_user_model()


class Comment(models.Model):
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Polymorphic relationship to Post, Say, or Pin
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return f"Comment by {self.author} on {self.content_object}"


class Post(models.Model):
    title = models.CharField(max_length=200, null=True, blank=True)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    comments = GenericRelation(Comment)
    comments_enabled = models.BooleanField(default=True)

    def get_absolute_url(self):
        return reverse("write:post_detail", args=[str(self.id)])

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Activity.objects.create(
                user=self.author,
                activity_type="post",
                content_object=self,
            )


class Say(models.Model):
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    comments = GenericRelation(Comment)
    comments_enabled = models.BooleanField(default=True)

    def get_absolute_url(self):
        return reverse("write:say_detail", args=[str(self.id)])

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Activity.objects.create(
                user=self.author,
                activity_type="say",
                content_object=self,
            )


class Pin(models.Model):
    title = models.TextField()
    url = models.URLField()
    content = models.TextField(null=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    comments = GenericRelation(Comment)
    comments_enabled = models.BooleanField(default=True)

    def get_absolute_url(self):
        return reverse("write:pin_detail", args=[str(self.id)])

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Activity.objects.create(
                user=self.author,
                activity_type="pin",
                content_object=self,
            )


@receiver(post_delete, sender=Post)
@receiver(post_delete, sender=Say)
@receiver(post_delete, sender=Pin)
def delete_activity(sender, instance, **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    Activity.objects.filter(content_type=content_type, object_id=instance.id).delete()
