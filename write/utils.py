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


# def get_visible_checkins(user, content_object, CheckInModel):
#     checkins = CheckInModel.objects.filter(
#         content_type=ContentType.objects.get_for_model(content_object),
#         object_id=content_object.id,
#     )

#     if user.is_authenticated:
#         checkins = checkins.filter(Q(visibility="PU") | Q(visible_to=user))
#     else:
#         checkins = checkins.filter(visibility="PU")

#     return checkins.order_by("-timestamp")


def get_visible_checkins(
    request_user, CheckInModel, content_type=None, object_id=None, checkin_user=None
):

    if checkin_user:
        if content_type is None or object_id is None:
            checkins = CheckInModel.objects.filter(
                user=checkin_user,
            )
        else:
            checkins = CheckInModel.objects.filter(
                content_type=content_type,
                object_id=object_id,
                user=checkin_user,
            )
    else:
        checkins = CheckInModel.objects.filter(
            content_type=content_type,
            object_id=object_id,
        )

    if request_user.is_authenticated:
        checkins = checkins.filter(Q(visibility="PU") | Q(visible_to=request_user))
    else:
        checkins = checkins.filter(visibility="PU")

    return checkins
