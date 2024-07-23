# Sets environment variables, changes directory and activates venv
# for gregor apps dev env
# Used by crontab, validate any changes

export DJANGO_SITE_DIR=/var/www/django/primed_apps_dev/
export DJANGO_SITE_USER=primedweb
export DJANGO_SETTINGS_MODULE=config.settings.apps_dev
export DJANGO_WSGI_FILE=config/primed_apps_dev_wsgi.py
export DJANGO_CRONTAB=primed_apps_dev.cron
export GAC_ENV=primed_apps_dev
cd $DJANGO_SITE_DIR
. venv/bin/activate
