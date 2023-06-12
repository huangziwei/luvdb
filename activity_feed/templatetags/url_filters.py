from urllib.parse import urlparse

from django import template

register = template.Library()


@register.filter
def root_url(url):
    return urlparse(url).scheme + "://" + urlparse(url).netloc
