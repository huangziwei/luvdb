import pytz
from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import Resolver404, resolve
from django.utils import timezone

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

    def __call__(self, request: HttpRequest):
        domain = request.get_host().split(":")[0]

        try:
            user = CustomUser.objects.get(custom_domain=domain)

            # Special handling for the login path
            if request.path_info == "/login/" or request.path_info == "/login":
                request.path_info = "/alt/login/"
            else:
                # Base path for the alternative profile
                base_user_path = f"/alt/@{user.username}/"
                # Append the original path to the base path
                new_path = base_user_path + request.path_info.lstrip("/")
                # Directly modify the request's path_info
                request.path_info = new_path

            # Process the modified request
            return self.get_response(request)

        except CustomUser.DoesNotExist:
            # If no custom domain match, continue as normal
            pass

        return self.get_response(request)
