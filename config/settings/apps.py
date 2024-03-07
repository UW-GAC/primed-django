import sys

from .production import *  # noqa
from .production import LOGGING, SOCIALACCOUNT_PROVIDERS, env  # noqa

# Log to file if we are in mod_wsgi. How to determine if in mod_wsgi
# https://modwsgi.readthedocs.io/en/develop/user-guides/assorted-tips-and-tricks.html#determining-if-running-under-mod-wsgi

LOGGING["root"]["level"] = "DEBUG"

try:
    from mod_wsgi import version  # noqa

    LOGGING["handlers"]["console"]["class"] = "logging.FileHandler"
    LOGGING["handlers"]["console"]["filename"] = "/var/log/django/primed-apps.log"

except ImportError:
    LOGGING["handlers"]["console"]["class"] = "logging.StreamHandler"
    # Send stream logging to stdout so we can redirect exceptions to email
    LOGGING["handlers"]["console"]["stream"] = sys.stdout

# Update drupal oauth api url for production
DRUPAL_SITE_URL = "https://primedconsortium.org"
SOCIALACCOUNT_PROVIDERS["drupal_oauth_provider"]["API_URL"] = DRUPAL_SITE_URL

LIVE_SITE = True
