import re
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
    if value is None:
        return "Unknown"

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


@register.filter(name="parse_range")
def parse_range(value):
    """Parses a range string into a list of integers."""
    if value is None:
        return []

    if "-" in value:
        return value.split("-")[0]
    else:
        return value


@register.filter
def is_period(publication_date):
    """
    Determine if the publication_date represents a period (range) or a single date.
    """
    # Regex pattern to match a date range with various formats:
    # e.g., YYYY-YYYY, YYYY.MM-YYYY.MM, YYYY.MM.DD-YYYY.MM.DD, including BCE dates
    pattern = r"^-?\d{1,4}(\.\d{2})?(\.\d{2})?--?\d{1,4}(\.\d{2})?(\.\d{2})?$"
    return bool(re.match(pattern, publication_date))
