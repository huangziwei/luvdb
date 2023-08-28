from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Person


class PersonSiteMap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Person.objects.all().order_by("-updated_at", "id")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("entity:person_detail", args=[obj.id])
