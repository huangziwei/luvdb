from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Book


class BookSiteMap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Book.objects.all().order_by("-updated_at", "id")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("read:book_detail", args=[obj.id])
