import re

import markdown
from django import template
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def linkify_tags(value):
    md = markdown.Markdown(extensions=["fenced_code"])

    def replace(match):
        tag = match.group(1)
        url = reverse("write:tag_list", args=[tag])
        return f'<a href="{url}">#{tag}</a>'

    def replacer(m):
        if m.group(1):  # it's a code block, ignore
            return m.group(0)
        else:  # it's not a code block, replace hashtags
            return re.sub(r"#(\w+)", replace, m.group(2))

    # Parse the markdown text and replace the hashtags
    html = md.convert(value)
    html = re.sub(
        r"(<pre><code>.*?</code></pre>)|([^<]+)", replacer, html, flags=re.DOTALL
    )

    return mark_safe(html)


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
