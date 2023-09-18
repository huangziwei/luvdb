from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.syndication.views import Feed
from django.http import Http404
from django.urls import reverse

from .models import Activity

User = get_user_model()


class UserActivityFeed(Feed):
    def __call__(self, request, *args, **kwargs):
        user = self.get_object(request, *args, **kwargs)
        if not user.is_public:
            raise Http404("This feed is private.")
        return super().__call__(request, *args, **kwargs)

    def get_object(self, request, username):
        return User.objects.get(username=username)

    def title(self, user):
        return f"{user.username}'s Activity feed at LʌvDB"

    def link(self, user):
        return reverse(
            "accounts:feed", args=[user.username]
        )  # You may want to change this link to something more generic

    def description(self, user):
        return f"Latest activities by {user.username} on LʌvDB"

    def items(self, user):
        return Activity.objects.filter(user=user).order_by("-timestamp")[:25]

    def item_title(self, activity):
        related_object = activity.content_object
        related_model = ContentType.objects.get_for_id(
            activity.content_type_id
        ).model_class()
        model_name = related_model.__name__.lower()
        if hasattr(related_object, "title"):
            return related_object.title
        elif hasattr(related_object, "content"):
            return related_object.content[:300]
        elif model_name == "follow":
            return f"{related_object.follower.username} followed {related_object.followed.username}"
        else:
            return related_object.followed.username

    def item_description(self, activity):
        related_object = activity.content_object
        related_model = ContentType.objects.get_for_id(
            activity.content_type_id
        ).model_class()
        model_name = related_model.__name__.lower()
        if hasattr(related_object, "content"):
            return related_object.content
        elif model_name == "follow":
            return f"{related_object.follower.username} followed {related_object.followed.username}"
        else:
            return str(related_object)

    def item_link(self, activity):
        related_model = ContentType.objects.get_for_id(
            activity.content_type_id
        ).model_class()
        related_object = related_model.objects.get(pk=activity.object_id)
        app_label = related_model._meta.app_label
        model_name = related_model.__name__.lower()

        # Dynamically set the URL reverse pattern based on the model name
        mapping = {
            "say": "write:say_detail",
            "post": "write:post_detail",
            "pin": "write:pin_detail",
            "repost": "write:repost_detail",
            "gamecheckin": "play:game_checkin_detail",
            "readcheckin": "read:read_checkin_detail",
            "watchcheckin": "watch:watch_checkin_detail",
            "listencheckin": "listen:listen_checkin_detail",
            "follow": "accounts:detail",
        }

        url_name = mapping.get(model_name)
        if url_name is None:
            raise ValueError(f"Unknown model name: {model_name}")

        if model_name != "follow":
            return reverse(url_name, args=[related_object.pk])
        else:
            return reverse(url_name, args=[related_object.followed.username])

    def item_pubdate(self, activity):
        return activity.content_object.timestamp
