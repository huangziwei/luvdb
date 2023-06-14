from django import template

register = template.Library()


@register.filter
def past_tense(value):
    if value == "say":
        return "said"
    elif value == "post":
        return "posted"
    elif value == "pin":
        return "pinned"
    elif value == "repost":
        return "reposted"
    else:
        return value
