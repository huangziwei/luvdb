import json
import sys

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.contrib.sitemaps.views import sitemap
from django.http import Http404, HttpResponse, HttpResponseServerError
from django.shortcuts import redirect
from django.template import loader
from django.urls import include, path, re_path, reverse
from django.utils.decorators import method_decorator
from django.views import View

from accounts.views import (
    CustomLoginView,
    InvitationRequestedSuccessView,
    InvitationRequestedView,
    ManageInvitationRequestsView,
    RequestInvitationView,
    SignUpView,
    generate_authentication_view,
    generate_registration_view,
    get_followed_usernames,
    get_user_tags,
    search_view,
    verify_authentication_view,
    verify_registration_view,
)
from entity.sitemaps import PersonSiteMap
from listen.sitemaps import ReleaseSiteMap
from play.sitemaps import GameSiteMap
from read.sitemaps import BookSiteMap, InstanceSiteMap, LitWorkSiteMap
from watch.sitemaps import MovieSiteMap, SeriesSiteMap
from write.models import LuvList

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


def custom_500_view(request, *args, **argv):
    template = loader.get_template("500.html")
    type_, value, traceback = sys.exc_info()

    return HttpResponseServerError(template.render({"error_message": str(value)}))


def redirect_to_at_username(request, username, extra_path=""):
    # Add a slash to extra_path if it's not empty
    extra_path = "/" + extra_path if extra_path else ""
    return redirect(f"/@{username}{extra_path}")


class RedirectToYearInReview(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        username = request.user.username
        return redirect(
            reverse("accounts:year_in_review", kwargs={"username": username})
        )


class RedirectToAccountUpdate(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        username = request.user.username
        return redirect(reverse("accounts:update", kwargs={"username": username}))


def site_manifest(request):
    data = {
        "name": "LʌvDB",
        "short_name": "LʌvDB",
        "display": "standalone",
        "icons": [
            {
                "src": "https://img-luvdb.s3.amazonaws.com/static/img/android-chrome-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": "https://img-luvdb.s3.amazonaws.com/static/img/android-chrome-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
        "theme_color": "#ffffff",
        "background_color": "#ffffff",
    }
    return HttpResponse(json.dumps(data), content_type="application/json")


urlpatterns = [
    # admin
    path("admin/login/", custom_admin_login, name="custom_admin_login"),
    path("admin/", admin.site.urls),
    # accounts
    path("signup/", SignUpView.as_view(), name="signup"),
    path("@", include("accounts.urls")),
    path(
        "u/<str:username>/",
        include(
            [
                path("", redirect_to_at_username, name="redirect_to_at_username"),
                re_path(r"^(?P<extra_path>.+)$", redirect_to_at_username),
            ]
        ),  # Redirect to @username
    ),
    path(
        "year-in-review/",
        RedirectToYearInReview.as_view(),
        name="redirect_to_year_in_review",
    ),
    path(
        "update/",
        RedirectToAccountUpdate.as_view(),
        name="redirect_to_account_update",
    ),
    # utils
    path(
        "get_followed_usernames/", get_followed_usernames, name="get_followed_usernames"
    ),
    path("get_user_tags/", get_user_tags, name="get_user_tags"),
    # requrest invitation
    path(
        "request-invitation/",
        RequestInvitationView.as_view(),
        name="request_invitation",
    ),
    path(
        "invitation-requested/<str:email>/",
        InvitationRequestedView.as_view(),
        name="invitation_requested",
    ),
    path(
        "invitation-requested-success/",
        InvitationRequestedSuccessView.as_view(),
        name="invitation_requested_success",
    ),
    path(
        "manage-invitation-requests/",
        ManageInvitationRequestsView.as_view(),
        name="manage_invitation_requests",
    ),
    # alt profile
    path("alt/", include("altprofile.urls")),
    # passkeys
    path(
        "passkey/generate_registration/",
        generate_registration_view,
        name="generate_registration",
    ),
    path(
        "passkey/verify_registration/",
        verify_registration_view,
        name="verify_registration",
    ),
    path(
        "passkey/generate_authentication/",
        generate_authentication_view,
        name="generate_authentication",
    ),
    path(
        "passkey/verify_authentication/",
        verify_authentication_view,
        name="verify_authentication",
    ),
    # apps
    path("entity/", include("entity.urls")),
    path("read/", include("read.urls")),
    path("play/", include("play.urls")),
    path("listen/", include("listen.urls")),
    path("watch/", include("watch.urls")),
    path("discover/", include("discover.urls")),
    path("", include("activity_feed.urls")),
    path("", include("write.urls")),
    path("search/", search_view, name="search"),
    path("notify/", include("notify.urls")),
    path("api/", include("api.urls")),
    path("visit/", include("visit.urls")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("site.webmanifest", site_manifest, name="site-manifest"),
    path("auth/", include("django.contrib.auth.urls")),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("", include("pages.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = "django.views.defaults.page_not_found"
handler500 = custom_500_view
