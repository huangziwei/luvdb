from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Game


class GameSiteMap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Game.objects.all().order_by("-updated_at")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("play:game_detail", args=[obj.id])
