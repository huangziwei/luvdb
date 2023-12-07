import pytz
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import Resolver404, resolve
from django.utils import timezone
from django_hosts import reverse

from accounts.models import CustomUser


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            tzname = request.user.timezone
            if tzname:
                timezone.activate(pytz.timezone(tzname))
            else:
                timezone.deactivate()
        return self.get_response(request)


class CustomDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        domain = request.get_host().split(":")[0]

        try:
            user = CustomUser.objects.get(custom_domain=domain)
            # Get the internal path for the alternative profile
            request.META["HTTP_HOST"] = settings.HTTP_HOST
            request.path_info = f"/@{user.username}/"  # Update the path for routing
        except CustomUser.DoesNotExist:
            pass  # If no custom domain match, continue as normal

        return self.get_response(request)


class AppendSlashAltMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the host is the 'alt' subdomain and the path doesn't end with a slash
        if "alt" in request.get_host() and not request.path.endswith("/"):
            # Check if the request is not an AJAX request
            if request.META.get("HTTP_X_REQUESTED_WITH") != "XMLHttpRequest":
                new_path = f"{request.path}/"
                if request.GET:
                    new_path += f"?{request.GET.urlencode()}"
                return HttpResponseRedirect(new_path)

        # Continue processing the request if the conditions are not met
        return self.get_response(request)
