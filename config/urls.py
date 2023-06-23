from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),  # Updated home view
    path("", include("accounts.urls")),
    path("entity/", include("entity.urls")),
    path("write/", include("write.urls")),
    path("read/", include("read.urls")),
    path("play/", include("play.urls")),
    path("feed/", include("activity_feed.urls")),
    path("", include("notify.urls")),
    path("", include("django.contrib.auth.urls")),  # Moved to the end
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = "django.views.defaults.page_not_found"
