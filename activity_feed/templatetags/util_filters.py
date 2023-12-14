from urllib.parse import urlparse

from django import template

register = template.Library()


@register.filter
def root_url(url):
    return urlparse(url).scheme + "://" + urlparse(url).netloc


@register.filter(name="extract_year")
def extract_year(value):
    """Extracts the year from a string formatted as 'YYYY.MM.DD' or 'YYYY.MM'."""
    return value.split(".")[0] if value and "." in value else value
