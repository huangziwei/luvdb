from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from .models import Comment


def get_visible_comments(user, content_object):
    comments = Comment.objects.filter(
        content_type=ContentType.objects.get_for_model(content_object),
        object_id=content_object.id,
    )

    if user.is_authenticated:
        comments = comments.filter(Q(visibility=Comment.PUBLIC) | Q(visible_to=user))
    else:
        comments = comments.filter(visibility=Comment.PUBLIC)

    return comments.distinct().order_by("timestamp")
