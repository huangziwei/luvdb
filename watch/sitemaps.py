from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Movie, Series


class MovieSiteMap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Movie.objects.all().order_by("-updated_at")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("watch:movie_detail", args=[obj.id])


class SeriesSiteMap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Series.objects.all().order_by("-updated_at")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("watch:series_detail", args=[obj.id])
