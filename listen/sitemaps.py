from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Release


class ReleaseSiteMap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Release.objects.all().order_by("-updated_at", "id")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("listen:release_detail", args=[obj.id])
