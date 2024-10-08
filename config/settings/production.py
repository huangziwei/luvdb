# config/settings/production.py

from .base import *

DEBUG = False

AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")
AWS_S3_CUSTOM_DOMAIN = env.str("AWS_S3_CUSTOM_DOMAIN")
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=31536000",  # 1 year
}
AWS_LOCATION = "static"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static/"),
]
STATIC_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
# STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "https://%s/media/" % (AWS_S3_CUSTOM_DOMAIN)
# DEFAULT_FILE_STORAGE = "config.s3_storage_backends.MediaStorage"

STORAGES = {
    "default": {
        "BACKEND": "config.s3_storage_backends.MediaStorage",
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
}

CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = ["https://luvdb.fly.dev/", "https://luvdb.com"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = True  # should be a boolean
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True

TEMPLATE_404 = "404.html"

ROOT_URL = "https://luvdb.com"
HTTP_HOST = "luvdb.com"
CORS_ALLOWED_ORIGINS = [
    "https://luvdb.com",
]

WEBAUTHN_RP_ID = "luvdb.com"
WEBAUTHN_RP_NAME = "luvdb"
