from django.contrib.auth import get_user_model
from django.contrib.syndication.views import Feed
from django.http import Http404
from django.urls import reverse

from .models import Pin, Post, Say

User = get_user_model()


class UserSayFeed(Feed):
    def __call__(self, request, *args, **kwargs):
        user = self.get_object(request, *args, **kwargs)
        if not user.is_public:
            raise Http404("This feed is private.")
        return super().__call__(request, *args, **kwargs)

    def get_object(self, request, username):
        return User.objects.get(username=username)

    def title(self, user):
        return f"{user.username}'s Say feed at LʌvDB"

    def link(self, user):
        return reverse("write:say_list", args=[user.username])

    def description(self, user):
        return f"Latest says by {user.username} on LʌvDB"

    def items(self, user):
        return Say.objects.filter(user=user).order_by("-timestamp")[:25]

    def item_title(self, say):
        return say.content[:50]  # Taking the first 50 characters.

    def item_description(self, say):
        return say.content

    def item_link(self, say):
        return reverse("write:say_detail", args=[say.pk])

    def item_pubdate(self, say):
        return say.timestamp


class UserPostFeed(Feed):
    def __call__(self, request, *args, **kwargs):
        user = self.get_object(request, *args, **kwargs)
        if not user.is_public:
            raise Http404("This feed is private.")
        return super().__call__(request, *args, **kwargs)

    def get_object(self, request, username):
        return User.objects.get(username=username)

    def title(self, user):
        return f"{user.username}'s Post feed at LʌvDB"

    def link(self, user):
        return reverse("write:post_list", args=[user.username])

    def description(self, user):
        return f"Latest posts by {user.username} on LʌvDB"

    def items(self, user):
        return Post.objects.filter(user=user).order_by("-timestamp")[:25]

    def item_title(self, post):
        return post.title  # Assuming 'Post' model has a 'title' field.

    def item_description(self, post):
        return post.content  # Assuming 'Post' model has a 'content' field.

    def item_link(self, post):
        return reverse("write:post_detail", args=[post.pk])

    def item_pubdate(self, post):
        return post.timestamp


class UserPinFeed(Feed):
    def __call__(self, request, *args, **kwargs):
        user = self.get_object(request, *args, **kwargs)
        if not user.is_public:
            raise Http404("This feed is private.")
        return super().__call__(request, *args, **kwargs)

    def get_object(self, request, username):
        return User.objects.get(username=username)

    def title(self, user):
        return f"{user.username}'s Pin feed at LʌvDB"

    def link(self, user):
        return reverse("write:pin_list", args=[user.username])

    def description(self, user):
        return f"Latest pins by {user.username} on LʌvDB"

    def items(self, user):
        return Pin.objects.filter(user=user).order_by("-timestamp")[:25]

    def item_title(self, pin):
        return pin.title  # Assuming 'Pin' model has a 'title' field.

    def item_description(self, pin):
        return pin.description  # Assuming 'Pin' model has a 'description' field.

    def item_link(self, pin):
        return reverse("write:pin_detail", args=[pin.pk])

    def item_pubdate(self, pin):
        return pin.timestamp
