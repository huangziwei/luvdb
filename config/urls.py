from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import redirect_to_login
from django.contrib.sitemaps.views import sitemap
from django.http import Http404
from django.urls import include, path

from accounts.views import home
from entity.sitemaps import PersonSiteMap
from listen.sitemaps import ReleaseSiteMap
from play.sitemaps import GameSiteMap
from read.sitemaps import BookSiteMap, InstanceSiteMap, LitWorkSiteMap
from watch.sitemaps import MovieSiteMap, SeriesSiteMap

sitemaps = {
    "entity": PersonSiteMap,
    "litworks": LitWorkSiteMap,
    "instances": InstanceSiteMap,
    "books": BookSiteMap,
    "games": GameSiteMap,
    "movies": MovieSiteMap,
    "releases": ReleaseSiteMap,
    "series": SeriesSiteMap,
}


def custom_admin_login(request):
    # If user is already logged in and is staff
    if request.user.is_authenticated and request.user.is_staff:
        return redirect_to_login(request.get_full_path(), "admin:index")

    # Otherwise, raise 404 error
    raise Http404


urlpatterns = [
    path("admin/login/", custom_admin_login, name="custom_admin_login"),
    path("admin/", admin.site.urls),
    path("", home, name="home"),  # Updated home view
    path("", include("accounts.urls")),
    path("entity/", include("entity.urls")),
    path("write/", include("write.urls")),
    path("read/", include("read.urls")),
    path("play/", include("play.urls")),
    path("listen/", include("listen.urls")),
    path("watch/", include("watch.urls")),
    path("feed/", include("activity_feed.urls")),
    path("", include("notify.urls")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("", include("django.contrib.auth.urls")),  # Moved to the end
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = "django.views.defaults.page_not_found"
