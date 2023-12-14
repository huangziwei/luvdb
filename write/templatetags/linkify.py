import re

from django import template
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def linkify_tags(value, user=None):
    # Function to replace hashtags
    def replace(match):
        tag = match.group(1)
        if user is not None:
            url = reverse("write:tag_user_list", args=[user.username, tag])
        else:
            url = reverse("write:tag_list", args=[tag])
        return f'<a href="{url}" class="text-success">#{tag}</a>'

    # Function to process text segments
    def process_text_segment(segment):
        return re.sub(r"#(\w+)", replace, segment)

    # Split the content using a regex that matches HTML tags, blockquotes, and code blocks
    pattern = r"(</?[^>]+>|```.*?```|<blockquote>.*?</blockquote>)"
    parts = re.split(pattern, value, flags=re.DOTALL)

    # Process only the non-matching parts (which are text outside HTML, blockquote, and code blocks)
    for i in range(len(parts)):
        if not re.match(pattern, parts[i]):
            parts[i] = process_text_segment(parts[i])

    # Join the parts back together
    processed_value = "".join(parts)
    return mark_safe(processed_value)


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

    return mark_safe(re.sub(r"(?<![:/])@(\w+)", replace, value))
