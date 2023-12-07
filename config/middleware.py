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
