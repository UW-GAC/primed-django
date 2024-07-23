export DJANGO_SITE_DIR=/var/www/django/primed_apps/
export DJANGO_SITE_USER=primedweb
export DJANGO_SETTINGS_MODULE=config.settings.apps
export DJANGO_WSGI_FILE=config/primed_apps_wsgi.py
export DJANGO_CRONTAB=primed_apps.cron
export GAC_ENV=primed_apps
cd $DJANGO_SITE_DIR
. venv/bin/activate
