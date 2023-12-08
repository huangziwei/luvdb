from django.conf import settings
from django.shortcuts import redirect
from django.urls import include, path, re_path


def redirect_to_default_host(request, path):
    return redirect(settings.ROOT_URL + f"/{path}")


urlpatterns = [
    path("", include("altprofile.urls")),
    # Catch-all pattern for any other paths
    re_path(r"^(?P<path>.*)$", redirect_to_default_host),
]
