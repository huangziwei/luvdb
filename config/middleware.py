import logging

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


# Create or get the logger
logger = logging.getLogger(__name__)


class LogIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the IP address from X-Forwarded-For if behind a proxy, otherwise use REMOTE_ADDR
        ip_address = request.META.get("HTTP_X_FORWARDED_FOR")
        if ip_address:
            ip_address = ip_address.split(",")[
                0
            ]  # Take the first IP in the list if there are multiple
        else:
            ip_address = request.META.get("REMOTE_ADDR")

        # Process the request
        response = self.get_response(request)

        # Log the IP address and the response status code
        if response.status_code == 403:
            logger.warning(f"403 Forbidden request from IP: {ip_address}")
        elif response.status_code == 404:
            logger.warning(f"404 Not Found request from IP: {ip_address}")
        elif 300 <= response.status_code < 400:
            logger.warning(
                f"{response.status_code} Redirect request from IP: {ip_address}"
            )

        return response
