from .base import *  # noqa
from .base import CACHES, env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="UCGPnfgK8eybDm7SByrfEdTdiLZSe1R1ueOKTevKZznloHWrnrYZfTkWEHuf1y2R",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES["default"] = {
    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    "LOCATION": "",
}

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")

# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS  # noqa F405


# django-debug-toolbar
# ------------------------------------------------------------------------------
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
INSTALLED_APPS += ["debug_toolbar"]  # noqa F405
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa F405
# https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
    "SHOW_TEMPLATE_CONTEXT": True,
}
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]


# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]  # noqa F405

# django-login-required-middleware login not required views
# allow debug panel viewing for non-logged in users in dev
LOGIN_REQUIRED_IGNORE_VIEW_NAMES += [  # noqa F405
    "djdt:template_source",
    "djdt:render_panel",
]

# Your stuff...
# ------------------------------------------------------------------------------
# Specify the path to the service account to use for managing access on AnVIL.
ANVIL_API_SERVICE_ACCOUNT_FILE = env("ANVIL_API_SERVICE_ACCOUNT_FILE")
# ANVIL_DBGAP_APPLICATION_GROUP_PREFIX = env(
#     "ANVIL_DBGAP_APPLICATION_GROUP_PREFIX", default="DEV_PRIMED_DBGAP_ACCESS"
# )
# ANVIL_CDSA_GROUP_PREFIX = env(
#     "ANVIL_CDSA_GROUP_PREFIX", default="DEV_PRIMED_CDSA_ACCESS"
# )
ANVIL_DATA_ACCESS_GROUP_PREFIX = env("ANVIL_DATA_ACCESS_GROUP_PREFIX", default="DEV_PRIMED")
ANVIL_CDSA_GROUP_NAME = env("ANVIL_CDSA_GROUP_NAME", default="DEV_PRIMED_CDSA")
ANVIL_CC_ADMINS_GROUP_NAME = env("ANVIL_CC_ADMINS_GROUP_NAME", default="DEV_PRIMED_CC_ADMINS")
