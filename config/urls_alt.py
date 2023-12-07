from django.conf import settings
from django.shortcuts import redirect
from django.urls import path, re_path

from accounts.views import AltAccountDetailView


def redirect_to_default_host(request, path):
    return redirect(settings.ROOT_URL + f"/{path}")


urlpatterns = [
    path(
        "@<str:username>/",
        AltAccountDetailView.as_view(),
        name="alt_account_detail",
    ),
    # Catch-all pattern for any other paths
    re_path(r"^(?P<path>.*)$", redirect_to_default_host),
]
