from django import template

register = template.Library()


@register.filter
def parse_activity_type(value):
    if value == "say":
        return "said"
    elif value == "post":
        return "posted"
    elif value == "pin":
        return "pinned"
    elif value == "repost":
        return "reposted"
    elif "check-in" in value:
        return "checked in"
    else:
        return value
