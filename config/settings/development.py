# config/settings/development.py

from .base import *

DEBUG = True

STATIC_URL = "/static/luvdb/"
STATIC_ROOT = BASE_DIR / "static/luvdb"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

SECURE_HSTS_SECONDS = False
SECURE_SSL_REDIRECT = False
CSRF_COOKIE_SECURE = False

ROOT_URL = "http://localhost:8000"
WEBAUTHN_RP_ID = "localhost"
WEBAUTHN_RP_NAME = "luvdb"
