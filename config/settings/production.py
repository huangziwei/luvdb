# config/settings/production.py

from .base import *

DEBUG = False

AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")
AWS_S3_CUSTOM_DOMAIN = "%s.s3.amazonaws.com" % AWS_STORAGE_BUCKET_NAME
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=604800",
}
AWS_LOCATION = "static"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static/luvdb"),
]
STATIC_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

MEDIA_URL = "https://%s/media/" % (AWS_S3_CUSTOM_DOMAIN)
DEFAULT_FILE_STORAGE = "config.s3_storage_backends.MediaStorage"

CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = ["https://*.fly.dev/", "https://*.luvdb.com"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = True  # should be a boolean
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True

TEMPLATE_404 = "404.html"

ROOT_URL = "https://luvdb.com"
