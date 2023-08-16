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


STATUS_CLASSES = {
    # Reading Status
    "to_read": "text-bg-info",
    "reading": "text-bg-primary",
    "finished_reading": "text-bg-success",
    "rereading": "text-bg-primary",
    "reread": "text-bg-success",
    # Watching Status
    "to_watch": "text-bg-info",
    "watching": "text-bg-primary",
    "watched": "text-bg-success",
    "rewatching": "text-bg-primary",
    "rewatched": "text-bg-success",
    # Listening Status
    "to_listen": "text-bg-info",
    "looping": "text-bg-primary",
    "listening": "text-bg-primary",
    "listened": "text-bg-success",
    "relistening": "text-bg-primary",
    "relistened": "text-bg-success",
    # Playing Status
    "to_play": "text-bg-info",
    "currently_playing": "text-bg-primary",
    "played": "text-bg-success",
    "replaying": "text-bg-primary",
    "replayed": "text-bg-success",
    # Shared Statuses
    "paused": "text-bg-warning",
    "abandoned": "text-bg-danger",
}


@register.filter(name="get_status_class")
def get_status_class(status):
    return STATUS_CLASSES.get(status, "text-bg-default")
