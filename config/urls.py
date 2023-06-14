from django.contrib import admin
from django.urls import include, path

from accounts.views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),  # Updated home view
    path("", include("accounts.urls")),
    path("write/", include("write.urls")),
    path("feed/", include("activity_feed.urls")),
    path("", include("notify.urls")),
    path("", include("django.contrib.auth.urls")),  # Moved to the end
]
