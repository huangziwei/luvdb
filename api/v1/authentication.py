from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from accounts.models import AppPassword


class AppPasswordAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.META.get("HTTP_X_APP_PASSWORD")
        if not token:
            return None

        try:
            app_password = AppPassword.objects.get(token=token)
        except AppPassword.DoesNotExist:
            raise AuthenticationFailed("Invalid App Password")

        return (app_password.user, None)
