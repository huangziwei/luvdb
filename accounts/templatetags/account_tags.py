from django import template
from django.db.models import Q

register = template.Library()


@register.filter
def is_following(user, other_user):
    if user.is_authenticated:
        return user.following.filter(followed=other_user).exists()
    else:
        return False


@register.filter
def is_blocking(user, other_user):
    if user.is_authenticated:
        return user.blocking.filter(blocked=other_user).exists()
    else:
        return False
