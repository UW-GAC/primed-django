"""
With these settings, tests run faster.
"""

from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="FWnaRrJxZ4c7Eg2vtMtPz7e3kNCPp4f1kaxY6xH8oJqoXPHilyOGsfwC0IPKd1de",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Your stuff...
# ------------------------------------------------------------------------------
ANVIL_API_SERVICE_ACCOUNT_FILE = "foo"
ANVIL_DATA_ACCESS_GROUP_PREFIX = "TEST_PRIMED"
ANVIL_CDSA_GROUP_NAME = "TEST_PRIMED_CDSA"

# template tests require debug to be set
# get the last templates entry and set debug option
TEMPLATES[-1]["OPTIONS"]["debug"] = True  # noqa
