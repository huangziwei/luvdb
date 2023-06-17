# config/settings/development.py

from .base import *

DEBUG = True

STATIC_URL = "/static/luvdb/"
STATIC_ROOT = BASE_DIR / "static/luvdb"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
