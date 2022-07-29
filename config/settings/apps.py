from .production import *  # noqa
from .production import LOGGING, env  # noqa

# Log to file if we are in mod_wsgi. How to determine if in mod_wsgi
# https://modwsgi.readthedocs.io/en/develop/user-guides/assorted-tips-and-tricks.html#determining-if-running-under-mod-wsgi

LOGGING["root"]["level"] = "DEBUG"

try:
    from mod_wsgi import version  # noqa

    LOGGING["handlers"]["console"]["class"] = "logging.FileHandler"
    LOGGING["handlers"]["console"]["filename"] = "/var/log/django/primed-apps.log"

except ImportError:
    LOGGING["handlers"]["console"]["class"] = "logging.StreamHandler"

# drupal oauth
SOCIALACCOUNT_PROVIDERS = {
    "drupal_oauth_provider": {
        "OVERRIDE_NAME": "Primed Consortium Site Login",
        "API_URL": "https://primedconsortium.org",
        "SCOPES": [
            {
                "drupal_machine_name": "oauth_django_access",
                "request_scope": False,
                "django_group_name": "test_django_access",
            },
        ],
    }
}
