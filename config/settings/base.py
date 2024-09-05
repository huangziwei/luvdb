"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 4.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

import os
from pathlib import Path

import pymdownx.arithmatex as arithmatex
import pymdownx.superfences as superfences
from environs import Env
from pymdownx.slugs import slugify

from write.utils_mdx import ImageExtension, MentionExtension, media_card

from ..s3_storage_backends import MediaStorage

env = Env()
env.read_env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY")
FERNET_KEY = env.str("FERNET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    "accounts",
    "dal",
    "dal_select2",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.syndication",
    "whitenoise.runserver_nostatic",  # 3rd party
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    # third-party apps
    "crispy_forms",
    "crispy_bootstrap5",
    "markdownify",
    "mathfilters",
    "storages",
    "corsheaders",
    "simple_history",
    "rest_framework",
    "sslserver",
    # local apps
    "notify",
    "activity_feed",
    "entity",
    "write",
    "read",
    "listen",
    "play",
    "watch",
    "discover",
    "api",
    "visit",
    "pages",
]

MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "config.middleware.LogIPMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.TimezoneMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "notify.middlewares.MarkNotificationReadMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "notify.context_processors.notifications",
                "config.context_processors.version_context",
                "config.context_processors.footer_links",
            ],
            "libraries": {
                "account_tags": "accounts.templatetags.account_tags",
                "util_filters": "activity_feed.templatetags.util_filters",
                "linkify": "write.templatetags.linkify",
                "parse_activity_type": "activity_feed.templatetags.parse_activity_type",
                "concat_sets": "read.templatetags.concat_sets",
                "language_name": "read.templatetags.language_name",
            },
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": env.dj_db_url("DATABASE_URL", default="sqlite:///db.sqlite3"),
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Berlin"

USE_I18N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.CustomUser"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_CLASS_CONVERTERS = {
    "form-select": "",
}


LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "activity_feed:activity_feed"
LOGOUT_REDIRECT_URL = "/login/"


# Markdownify settings
MARKDOWNIFY = {
    "default": {
        "WHITELIST_TAGS": [
            "abbr",
            "acronym",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "blockquote",
            "cite",
            "code",
            "em",
            "i",
            "strong",
            "var",
            "b",
            "i",
            "ul",
            "ol",
            "li",
            "dl",
            "dt",
            "dd",
            "img",
            "pre",
            "div",
            "span",
            "table",
            "thead",
            "tbody",
            "tfoot",
            "tr",
            "th",
            "td",
            "p",
            "hr",
            "br",
            "details",
            "summary",
            "caption",
            "col",
            "colgroup",
            "fieldset",
            "legend",
            "section",
            "article",
            "figure",
            "header",
            "footer",
            "aside",
            "center",
            "main",
            "nav",
            "output",
            "progress",
            "audio",
            "canvas",
            "ruby",
            "rt",
            "rp",
            "s",
            "strike",
            "del",
            "ins",
            "a",
            "small",
            "sup",
            "sub",
            "u",
            "mark",
            "time",
            "iframe",
            "link",
            "input",
            "label",
        ],
        "WHITELIST_ATTRS": [
            "src",
            "alt",
            "href",
            "title",
            "class",
            "id",
            "target",
            "height",
            "width",
            "rel",
            "checked",
            "name",
            "type",
            "data-tabs",
            "for",
        ],
        "WHITELIST_STYLES": [
            "color",
            "font-weight",
        ],
        "MARKDOWN_EXTENSIONS": [
            "pymdownx.superfences",
            "pymdownx.arithmatex",
            "pymdownx.highlight",
            "pymdownx.inlinehilite",
            "pymdownx.mark",
            "pymdownx.saneheaders",
            "pymdownx.escapeall",
            "pymdownx.betterem",
            "pymdownx.tilde",
            "pymdownx.blocks.tab",
            "pymdownx.blocks.details",
            "pymdownx.magiclink",
            "footnotes",
            "md_in_html",
            "nl2br",
            "toc",
            "tables",
            MentionExtension(),
            ImageExtension(),
        ],
        "MARKDOWN_EXTENSION_CONFIGS": {
            "pymdownx.superfences": {
                "preserve_tabs": True,
                "custom_fences": [
                    {
                        "name": "math",
                        "class": "arithmatex",
                        "format": arithmatex.arithmatex_fenced_format(which="generic"),
                    },
                    {
                        "name": "mermaid",
                        "class": "mermaid",
                        "format": superfences.fence_div_format,
                    },
                    {
                        "name": "card",
                        "class": "media-card",
                        "format": media_card,
                    },
                ],
            },
            "pymdownx.inlinehilite": {
                "custom_inline": [
                    {
                        "name": "math",
                        "class": "arithmatex",
                        "format": arithmatex.arithmatex_inline_format(which="generic"),
                    }
                ]
            },
            "pymdownx.blocks.tab": {
                "slugify": slugify(case="lower", percent_encode=True),
                "separator": "_",  # Separator of your choice
            },
        },
    }
}


REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.v1.authentication.AppPasswordAuthentication"
    ],
}

ROOT_HOSTCONF = "config.hosts"
DEFAULT_HOST = "root"

DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": "requests.log",
        },
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Log to stdout (captured by Fly.io)
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": True,
        },
        "config": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": True,
        },
    },
}
