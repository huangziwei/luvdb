from itertools import chain

import markdown
from django.contrib.auth import get_user_model
from django.contrib.syndication.views import Feed
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.safestring import mark_safe

from listen.models import ListenCheckIn
from play.models import PlayCheckIn
from read.models import ReadCheckIn
from watch.models import WatchCheckIn

from .models import Pin, Post, Repost, Say

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
        return f"{user.username}'s Say feed on LʌvDB"

    def link(self, user):
        return reverse("write:say_list", args=[user.username])

    def description(self, user):
        return f"Latest says by {user.username} on LʌvDB"

    def items(self, user):
        return Say.objects.filter(user=user, is_direct_mention=False).order_by(
            "-timestamp"
        )[:25]

    def item_title(self, say):
        return mark_safe(markdown.markdown(say.content))

    def item_description(self, say):
        return None

    def item_link(self, say):
        return reverse("write:say_detail", kwargs={"pk": say.pk, "username": say.user})

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
        return f"{user.username}'s Post feed on LʌvDB"

    def link(self, user):
        return reverse("write:post_list", args=[user.username])

    def description(self, user):
        return f"Latest posts by {user.username} on LʌvDB"

    def items(self, user):
        return Post.objects.filter(user=user).order_by("-timestamp")[:25]

    def item_title(self, post):
        return mark_safe(markdown.markdown(post.title))

    def item_description(self, post):
        return mark_safe(markdown.markdown(post.content))

    def item_link(self, post):
        return reverse(
            "write:post_detail", kwargs={"pk": post.pk, "username": post.user}
        )

    def item_pubdate(self, post):
        return post.timestamp


class UserPostProjectFeed(Feed):
    def __call__(self, request, *args, **kwargs):
        username = kwargs.get("username")
        project_name = kwargs.get("project")
        if not self.is_feed_public(username):
            raise Http404("This feed is private.")
        return super(UserPostProjectFeed, self).__call__(request, *args, **kwargs)

    def is_feed_public(self, username):
        user = User.objects.get(username=username)
        return user.is_public

    def get_object(self, request, username, project):
        return username, project

    def title(self, obj):
        username, project_name = obj
        return f"{username}'s {project_name} Post feed on LʌvDB"

    def link(self, obj):
        username, project_name = obj
        return reverse("write:post_list_project", args=[username, project_name])

    def description(self, obj):
        username, project_name = obj
        return f"Latest posts in project {project_name} by {username} on LʌvDB"

    def items(self, obj):
        username, project_name = obj
        return Post.objects.filter(
            user__username=username, projects__slug=project_name
        ).order_by("-timestamp")[:25]

    def item_title(self, post):
        return mark_safe(markdown.markdown(post.title))

    def item_description(self, post):
        return mark_safe(markdown.markdown(post.content))

    def item_link(self, post):
        return reverse(
            "write:post_detail", kwargs={"pk": post.pk, "username": post.user}
        )

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
        return f"{user.username}'s Pin feed on LʌvDB"

    def link(self, user):
        return reverse("write:pin_list", args=[user.username])

    def description(self, user):
        return f"Latest pins by {user.username} on LʌvDB"

    def items(self, user):
        return Pin.objects.filter(user=user).order_by("-timestamp")[:25]

    def item_title(self, pin):
        return pin.title

    def item_description(self, pin):
        return pin.content

    def item_link(self, pin):
        return reverse("write:pin_detail", kwargs={"pk": pin.pk, "username": pin.user})

    def item_pubdate(self, pin):
        return pin.timestamp


class TagListFeed(Feed):
    request = None  # Initialize request to None

    def __call__(self, request, *args, **kwargs):
        self.request = request  # Capture the request object
        return super().__call__(request, *args, **kwargs)

    def get_object(self, request, tag):
        return tag

    def title(self, tag):
        return f"Tag feed for {tag} on LʌvDB"

    def link(self, tag):
        return reverse("write:tag_list", args=[tag])

    def description(self, tag):
        return f"Latest activities tagged with {tag} on LʌvDB"

    def items(self, tag):
        # Initialize querysets
        posts = Post.objects.filter(tags__name=tag)
        says = Say.objects.filter(tags__name=tag)
        pins = Pin.objects.filter(tags__name=tag)
        read_checkins = ReadCheckIn.objects.filter(tags__name=tag)
        watch_checkins = WatchCheckIn.objects.filter(tags__name=tag)
        listen_checkins = ListenCheckIn.objects.filter(tags__name=tag)
        play_checkins = PlayCheckIn.objects.filter(tags__name=tag)
        reposts = Repost.objects.filter(tags__name=tag)

        # Combine all querysets into a single list and sort by timestamp
        combined_list = list(
            chain(
                posts,
                says,
                pins,
                read_checkins,
                watch_checkins,
                listen_checkins,
                play_checkins,
                reposts,
            )
        )
        sorted_list = sorted(combined_list, key=lambda x: x.timestamp, reverse=True)

        # Filter out items from non-public profiles if the user is not logged in
        if not self.request.user.is_authenticated:
            sorted_list = [item for item in sorted_list if item.user.is_public]

        return sorted_list[:25]

    def item_title(self, item):
        model_name = item.__class__.__name__.lower()
        if model_name == "say":
            return mark_safe(markdown.markdown(item.content))
        elif model_name == "post":
            return f'{item.user.username} posted "{item.title}"'
        elif model_name == "pin":
            return f'{item.user.username} pinned "{item.title}"'
        elif model_name == "follow":
            return f"{item.follower.username} followed {item.followed.username}"
        elif "checkin" in model_name:
            return f"{item.user.username} checked in to {item.content_object.title}"
        else:
            return str(item)

    def item_description(self, item):
        model_name = item.__class__.__name__.lower()
        if model_name == "say":
            return None
        if hasattr(item, "content"):
            return mark_safe(markdown.markdown(item.content))
        elif model_name == "follow":
            return f"{item.follower.username} followed {item.followed.username}"
        else:
            return str(item)

    def item_link(self, item):
        model_name = item.__class__.__name__.lower()
        mapping = {
            "say": "write:say_detail",
            "post": "write:post_detail",
            "pin": "write:pin_detail",
            "repost": "write:repost_detail",
            "playcheckin": "write:play_checkin_detail",
            "readcheckin": "write:read_checkin_detail",
            "watchcheckin": "write:watch_checkin_detail",
            "listencheckin": "write:listen_checkin_detail",
            "follow": "accounts:detail",
        }
        url_name = mapping.get(model_name)
        if url_name is None:
            raise ValueError(f"Unknown model name: {model_name}")

        if model_name != "follow":
            return reverse(url_name, args=[item.pk])
        else:
            return reverse(url_name, args=[item.followed.username])

    def item_pubdate(self, item):
        return item.timestamp


class TagUserListFeed(Feed):
    request = None  # Initialize request to None

    def __call__(self, request, *args, **kwargs):
        self.request = request  # Capture the request object
        user = self.get_object(request, *args, **kwargs)
        if not user.is_public:
            raise Http404("This feed is private.")
        return super().__call__(request, *args, **kwargs)

    def get_object(self, request, username, tag):
        self.user = get_object_or_404(get_user_model(), username=username)
        self.tag = tag
        return self.user

    def title(self, user):
        return f"Activity feed for tag {self.tag} by {user.username}"

    def link(self, user):
        return reverse("write:tag_user_list", args=[user.username, self.tag])

    def description(self, user):
        return f"Latest activities for tag {self.tag} by {user.username}"

    def items(self, user):
        tag = self.tag

        posts = Post.objects.filter(tags__name=tag, user=user)
        says = Say.objects.filter(tags__name=tag, user=user)
        pins = Pin.objects.filter(tags__name=tag, user=user)
        reposts = Repost.objects.filter(tags__name=tag, user=user)
        read_checkins = ReadCheckIn.objects.filter(tags__name=tag, user=user)
        watch_checkins = WatchCheckIn.objects.filter(tags__name=tag, user=user)
        listen_checkins = ListenCheckIn.objects.filter(tags__name=tag, user=user)
        play_checkins = PlayCheckIn.objects.filter(tags__name=tag, user=user)

        # Combine all querysets into a single list and sort by timestamp
        combined_list = list(
            chain(
                posts,
                says,
                pins,
                read_checkins,
                watch_checkins,
                listen_checkins,
                play_checkins,
                reposts,
            )
        )
        sorted_list = sorted(combined_list, key=lambda x: x.timestamp, reverse=True)

        return sorted_list[:25]  # Limit to 25 items

    def item_title(self, item):
        model_name = item.__class__.__name__.lower()
        if model_name == "say":
            return mark_safe(markdown.markdown(item.content))
        elif model_name == "post":
            return f'{item.user.username} posted "{item.title}"'
        elif model_name == "pin":
            return f'{item.user.username} pinned "{item.title}"'
        elif model_name == "follow":
            return f"{item.follower.username} followed {item.followed.username}"
        elif "checkin" in model_name:
            return f"{item.user.username} checked in to {item.content_object.title}"
        else:
            return str(item)

    def item_description(self, item):
        model_name = item.__class__.__name__.lower()
        if model_name == "say":
            return None
        if hasattr(item, "content"):
            return mark_safe(markdown.markdown(item.content))
        elif model_name == "follow":
            return f"{item.follower.username} followed {item.followed.username}"
        else:
            return str(item)

    def item_link(self, item):
        model_name = item.__class__.__name__.lower()
        mapping = {
            "say": "write:say_detail",
            "post": "write:post_detail",
            "pin": "write:pin_detail",
            "repost": "write:repost_detail",
            "playcheckin": "write:play_checkin_detail",
            "readcheckin": "write:read_checkin_detail",
            "watchcheckin": "write:watch_checkin_detail",
            "listencheckin": "write:listen_checkin_detail",
            "follow": "accounts:detail",
        }
        url_name = mapping.get(model_name)
        if url_name is None:
            raise ValueError(f"Unknown model name: {model_name}")

        if model_name != "follow":
            return reverse(url_name, args=[item.pk])
        else:
            return reverse(url_name, args=[item.followed.username])

    def item_pubdate(self, item):
        return item.timestamp
