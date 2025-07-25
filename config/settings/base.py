"""
Base settings to build other settings files upon.
"""

from pathlib import Path

import environ

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# primed/
APPS_DIR = ROOT_DIR / "primed"
env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    print(f"Initializing dotenv from {ROOT_DIR}")
    env.read_env(str(ROOT_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "America/Los_Angeles"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(ROOT_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///primed.db"),
}
# DATABASES["default"]["ATOMIC_REQUESTS"] = True
# # https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # "django.contrib.humanize", # Handy template tags
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "maintenance_mode",
    "login_required",
    # Tables
    "django_tables2",
    # Autocomplete.
    # note these are supposed to come before django.contrib.admin.
    "dal",
    "dal_select2",
    "fontawesomefree",
    # django-simple-history for model change tracking
    "simple_history",
    "dbbackup",
    "django_htmx",
    "constance",
]

LOCAL_APPS = [
    "anvil_consortium_manager",
    "anvil_consortium_manager.auditor",
    "primed.users.apps.UsersConfig",
    # Your stuff: custom apps go here
    "primed.drupal_oauth_provider",
    "primed.primed_anvil",
    "primed.dbgap",
    "primed.miscellaneous_workspaces",
    "primed.duo",
    "primed.cdsa",
    "primed.collaborative_analysis",
]

# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "primed.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "login_required.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "maintenance_mode.middleware.MaintenanceModeMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR / "static")]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR / "templates")],
        # https://docs.djangoproject.com/en/dev/ref/settings/#app-dirs
        "APP_DIRS": True,
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "constance.context_processors.config",
                "primed.utils.context_processors.settings_context",
            ],
        },
    }
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
# https://github.com/django-crispy-forms/crispy-bootstrap5
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""Primed Admins""", "primedweb@uw.edu")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"verbose": {"format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"}},
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# Django silence system check warnings. https://docs.djangoproject.com/en/5.1/ref/checks/#security
# This check is regarding constraints placed by django-allauth
# that mysql does not support. https://github.com/pennersr/django-allauth/issues/3385
# we would need to move to postgres to support this type of constraint with filter
SILENCED_SYSTEM_CHECKS = ["models.W036"]

# Caching
# ------------------------------------------------------------------------------
# See https://docs.djangoproject.com/en/dev/topics/cache/
CACHES = {
    # Add a cache specific for anvil_consortium_manager auditing:
    "anvil_audit": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "anvil_audit_cache",
        "OPTIONS": {
            "MAX_ENTRIES": 10000,  # Maximum number of entries in the cache.
        },
        "TIMEOUT": None,  # Cache entries never expire.
    },
}

# django-maintenance-mode
MAINTENANCE_MODE_IGNORE_SUPERUSER = True
MAINTENANCE_MODE_IGNORE_TESTS = True

# django-allauth
# ------------------------------------------------------------------------------
# https://docs.allauth.org/en/latest/account/configuration.html
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
ACCOUNT_LOGIN_METHODS = {"username"}
# ACCOUNT_EMAIL_REQUIRED = True
# Replaces above for new allauth signup.
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_ADAPTER = "primed.users.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "primed.users.adapters.SocialAccountAdapter"
ACCOUNT_EMAIL_VERIFICATION = "none"

# django-login-required-middleware login not required views
# limited set of views we allow a non-logged in user to access
LOGIN_REQUIRED_IGNORE_VIEW_NAMES = [
    "account_login",
    "drupal_oauth_provider_login",
    "drupal_oauth_provider_callback",
    "socialaccount_signup",
    "admin:index",
    "admin:login",
    "cdsa:records:index",
    "cdsa:records:representatives",
    "cdsa:records:studies",
    "cdsa:records:workspaces",
    "cdsa:records:user_access",
    "dbgap:records:index",
    "dbgap:records:applications",
    "favicon",
]

# django-dbbackup
DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
DBBACKUP_STORAGE_OPTIONS = {"location": ROOT_DIR / "dbbackups"}

# PRIMED
# ------------------------------------------------------------------------------
# Allauth
# SCOPES are the set of drupal roles/django groups managed by the drupal oauth provider.
# Scopes that are requested "request_scope=True" will be returned by the oauth server
# if the user has that drupal role.
# ** Note: Requested drupal scopes that do not exist will cause a drupal server error
# where the user will just land at the drupal site on the home page (check the drupal logs for errors in this case)
# The scopes 'oauth_client_user' and 'authenticated' automatically to anyone who logs in
# via oauth (as configured in the drupal consumer) and will be returned even if we do not request
# them but are not currently mapped to django groups.
DRUPAL_SITE_URL = "https://dev.primedconsortium.org"
SOCIALACCOUNT_PROVIDERS = {
    "drupal_oauth_provider": {
        "OVERRIDE_NAME": "Primed Consortium Site Login",
        "API_URL": DRUPAL_SITE_URL,
        "SCOPES": [
            {
                "drupal_machine_name": "dcc_staff",
                "request_scope": True,
                "django_group_name": "DCC Staff",
            },
            {
                "drupal_machine_name": "dcc_acm_admin",
                "request_scope": True,
                "django_group_name": "DCC ACM Admin",
            },
            # For now, grant the ACM AccountLink permission to any authenticated user.
            {
                "drupal_machine_name": "authenticated",
                "request_scope": True,
                "django_group_name": "Authenticated",
            },
        ],
    }
}

# Setting for whether the config represents the live production site (apps.gregorconsortium.org)
# Initially used to style all non dev sites differently
LIVE_SITE = False

# Help contact email
DCC_CONTACT_EMAIL = "primedconsortium@uw.edu"

# django-tables2
# ------------------------------------------------------------------------------
# https://django-tables2.readthedocs.io/en/latest/pages/custom-rendering.html?highlight=django_tables2_template#available-templates
DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap5.html"

# django-constance
# ------------------------------------------------------------------------------
CONSTANCE_CONFIG = {
    "ANNOUNCEMENT_TEXT": ("", "Site-wide announcement message", str),
}

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"
CONSTANCE_IGNORE_ADMIN_VERSION_CHECK = True
# CONSTANCE_DATABASE_CACHE_BACKEND = "default"
CONSTANCE_DATABASE_CACHE_AUTOFILL_TIMEOUT = None

# django-anvil-consortium-manager
# ------------------------------------------------------------------------------

# Specify workspace adapters.
ANVIL_WORKSPACE_ADAPTERS = [
    "primed.dbgap.adapters.dbGaPWorkspaceAdapter",
    "primed.cdsa.adapters.CDSAWorkspaceAdapter",
    "primed.miscellaneous_workspaces.adapters.OpenAccessWorkspaceAdapter",
    "primed.miscellaneous_workspaces.adapters.SimulatedDataWorkspaceAdapter",
    "primed.miscellaneous_workspaces.adapters.ResourceWorkspaceAdapter",
    "primed.miscellaneous_workspaces.adapters.ConsortiumDevelWorkspaceAdapter",
    "primed.collaborative_analysis.adapters.CollaborativeAnalysisWorkspaceAdapter",
    "primed.miscellaneous_workspaces.adapters.TemplateWorkspaceAdapter",
    "primed.miscellaneous_workspaces.adapters.DataPrepWorkspaceAdapter",
]
ANVIL_ACCOUNT_ADAPTER = "primed.primed_anvil.adapters.AccountAdapter"
ANVIL_MANAGED_GROUP_ADAPTER = "primed.primed_anvil.adapters.ManagedGroupAdapter"
ANVIL_AUDIT_CACHE = "anvil_audit"

DRUPAL_API_CLIENT_ID = env("DRUPAL_API_CLIENT_ID", default="")
DRUPAL_API_CLIENT_SECRET = env("DRUPAL_API_CLIENT_SECRET", default="")
DRUPAL_API_REL_PATH = env("DRUPAL_API_REL_PATH", default="mockapi")
DRUPAL_DATA_AUDIT_DEACTIVATE_USERS = env("DRUPAL_DATA_AUDIT_DEACTIVATE_USERS", default=False)
DRUPAL_DATA_AUDIT_REMOVE_USER_SITES = env("DRUPAL_DATA_AUDIT_REMOVE_USER_SITES", default=False)
