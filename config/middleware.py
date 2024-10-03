import logging
import re
import time

import pytz
from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponseForbidden,
    HttpResponseGone,
    HttpResponseRedirect,
)
from django.urls import Resolver404, resolve
from django.utils import timezone
from django_ratelimit.core import is_ratelimited

from accounts.models import BlockedIP, CustomUser


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
logger = logging.getLogger("config")


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

        # Get additional information for logging
        method = request.method  # GET, POST, etc.
        path = request.get_full_path()  # The full URL path (including query parameters)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        # Process the request and get the response
        response = self.get_response(request)

        # Allow access to robots.txt for all IPs, even blocked ones
        if request.path == "/robots.txt":
            logger.warning(
                f"IP: {ip_address} | User-Agent: {user_agent} | Method: {method} | Path: {path} | Status: {response.status_code}"
            )
            return self.get_response(request)

        # Check if the IP is blocked by querying the BlockedIP model
        if BlockedIP.objects.filter(ip_address=ip_address).exists():
            logger.warning(
                f"Blocked malicious IP: {ip_address} tried to access {request.path}"
            )
            return HttpResponseForbidden("Forbidden: Your IP is blocked.")

        # Handle deprecated endpointsq
        if re.match(r"^/u/[^/]+/inbox/$", request.path):
            # Add the IP to BlockedIP model if it tries to access this deprecated endpoint
            BlockedIP.objects.get_or_create(
                ip_address=ip_address,
                defaults={"reason": "Attempted access to deprecated /inbox/ endpoint."},
            )

            # Introduce a delay to slow down bots
            limited = is_ratelimited(
                request, group="deprecated_inbox", key="ip", rate="1/d", increment=True
            )
            if limited:
                logger.warning(f"Rate limited: {request.path} from IP: {ip_address}")
                return HttpResponseGone("Too many requests.")
            else:
                logger.warning(
                    f"Deprecated endpoint accessed: {request.path} from IP: {ip_address}"
                )
            return HttpResponseGone("This endpoint is no longer available.")

        # Log the IP address, request method, path, and status code for all requests
        logger.warning(
            f"IP: {ip_address} | User-Agent: {user_agent} | Method: {method} | Path: {path} | Status: {response.status_code}"
        )

        return response
