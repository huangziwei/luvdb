from django.contrib.auth import get_user_model
from django.contrib.syndication.views import Feed
from django.urls import reverse

from .models import Pin, Post, Say

User = get_user_model()


class UserSayFeed(Feed):
    title = "User's Say feed"
    link = "/users/says/"
    description = "Updates on user's says."

    def get_object(self, request, username):
        return User.objects.get(username=username)

    def items(self, user):
        return Say.objects.filter(user=user).order_by("-timestamp")[:10]

    def item_title(self, say):
        return say.content[:50]  # Taking the first 50 characters.

    def item_description(self, say):
        return say.content

    def item_link(self, say):
        return reverse("write:say_detail", args=[say.pk])


class UserPostFeed(Feed):
    title = "User's Post feed"
    link = "/users/posts/"  # This should be changed to the appropriate URL.
    description = "Updates on user's posts."

    def get_object(self, request, username):
        return User.objects.get(username=username)

    def items(self, user):
        return Post.objects.filter(user=user).order_by("-timestamp")[:10]

    def item_title(self, post):
        return post.title  # Assuming 'Post' model has a 'title' field.

    def item_description(self, post):
        return post.content  # Assuming 'Post' model has a 'content' field.

    def item_link(self, post):
        return reverse("write:post_detail", args=[post.pk])


class UserPinFeed(Feed):
    title = "User's Pin feed"
    link = "/users/pins/"  # This should be changed to the appropriate URL.
    description = "Updates on user's pins."

    def get_object(self, request, username):
        return User.objects.get(username=username)

    def items(self, user):
        return Pin.objects.filter(user=user).order_by("-timestamp")[:10]

    def item_title(self, pin):
        return pin.title  # Assuming 'Pin' model has a 'title' field.

    def item_description(self, pin):
        return pin.description  # Assuming 'Pin' model has a 'description' field.

    def item_link(self, pin):
        return reverse("write:pin_detail", args=[pin.pk])
