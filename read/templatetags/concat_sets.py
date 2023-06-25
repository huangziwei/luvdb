from itertools import chain

from django import template

register = template.Library()


@register.filter
def concat(value1, value2):
    return list(chain(value1, value2))


@register.filter
def hasattr(value, attr):
    return hasattr(value, attr)
