from urllib.parse import urlparse

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def root_url(url):
    return urlparse(url).scheme + "://" + urlparse(url).netloc


@register.filter(name="extract_year")
def extract_year(value):
    """Extracts the year from a string formatted as 'YYYY.MM.DD' or 'YYYY.MM'."""
    if "-" in value:
        return value.split("-")[0]
    elif "–" in value:
        return value.split("–")[0]
    else:
        return value.split(".")[0] if value and "." in value else value


@register.filter(name="daysince")
def daysince(timestamp):
    """Returns the number of days since the given timestamp."""
    return (timezone.now() - timestamp).days
