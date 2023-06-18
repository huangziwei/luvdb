import re

from django import template
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def linkify_tags(value):
    # Split the content by triple backticks to distinguish code blocks
    split_by_backticks = value.split("```")

    for i in range(len(split_by_backticks)):
        # If the index is even, it means this is not inside a code block.
        # Hence, replace the hashtags.
        if i % 2 == 0:

            def replace(match):
                tag = match.group(1)
                url = reverse("write:tag_list", args=[tag])
                return f'<a href="{url}">#{tag}</a>'

            split_by_backticks[i] = re.sub(r"#(\w+)", replace, split_by_backticks[i])

    # Join back the content
    value = "```".join(split_by_backticks)

    return mark_safe(value)


@register.filter
def linkify_mentions(value):
    def replace(match):
        username = match.group(1)
        try:
            user = get_user_model().objects.get(username=username)
            url = reverse("accounts:detail", args=[username])
            return f'<a href="{url}">@{username}</a>'
        except get_user_model().DoesNotExist:
            return f"@{username}"

    return mark_safe(re.sub(r"@(\w+)", replace, value))
