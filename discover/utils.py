from django.contrib.contenttypes.models import ContentType

from .models import Vote

###########
# helpers #
###########


def user_has_upvoted(user, obj):
    if not user.is_authenticated:
        return False

    content_type = ContentType.objects.get_for_model(obj)
    return Vote.objects.filter(
        user=user,
        content_type=content_type,
        object_id=obj.id,
        value=Vote.UPVOTE,
    ).exists()
