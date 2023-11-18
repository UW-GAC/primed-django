
# Primed Consortium Django Site

[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

[![image](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/pydanny/cookiecutter-django/)

## Setup Application

### Brief details on how to deploy this application in dev:

-   create virtualenv (python 3.8 or greater required)
    -   create virtualenv: python -m venv venv
    -   activate virtualenv: source venv/bin/activate
-   clone repository
-   cd into project root dir
-   python -m pip install pip-tools
-   pip-sync requirements/requirements.txt requirements/test-requirements.txt requirements/dev-requirements.txt
-   python manage.py migrate
-   python manage.py createsuperuser
-   python manage.py runserver_plus
-   visit your \<site url\>/admin to login as super user you just
    created
-   by default manage.py uses config/settings/local.py if you want
    custom config, you can create a username_local.py config file that
    includes local.py and use it by setting the following environment
    variable ie:
    -   export DJANGO_SETTINGS_MODULE=config.settings.username_local

### Enable oauth login for drupal if needed for your development work

-   [Configuration and setup instructions for drupal simple_oauth
    provider](primed/drupal_oauth_provider/docs/provider.md)
-   After configuring your site and creating a consumer, navigate to
    /admin
-   Add a Social Application to your django site
    -   Select \'Drupal Oauth2 Drupal Provider\'
    -   enter secret key and client ID captured when creating a drupal
        consumer
    -   leave \'key\' blank
    -   select site_id number 1 (by default example.com) as a chosen
        site
-   Open a different browser or browser private session (so not logged
    in as SU)
-   visit \<site_url\>
-   choose sign in via Drupal Provider
-   login at the oauth server site and follow instructions to grant
    permissions and create oauth account

### Troubleshooting

> Check your callback url. Your django development server may be running
> at <http://localhost:8000/accounts/github/login/callback/> instead of
> <http://127.0.0.1:8000/accounts/github/login/callback/>

Example:

    $ python manage.py runserver_plus
    Performing system checks...
    System check identified no issues (0 silenced).
    Django version 3.1.13, using settings 'config.settings.local'
    Development server is running at http://[127.0.0.1]:8000/

### Type checks

Running type checks with mypy:

    $ mypy primed

### Test coverage

To run the tests, check your test coverage, and generate an HTML
coverage report:

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html (git bash on windows use start instead of open)

Running tests with pytest and unittest

    $ pytest
    $ python manage.py test

### Basic steps to add/alter code

1.  git checkout -b \<feature_branch_name\> (Create and switch to
    feature branch)
2.  sync requirements: `pip-sync requirements/requirements.txt test-requirements.txt dev-requirements.txt`
3.  make changes, test changes, document changes, commit often
4.  run tests: pytest, python manage.py test
5.  test coverage: (see above)
6.  type checks: mypy primed
7.  git add your changes
8.  manually run pre-commit if you did not install
9.  git commit your changes
10.  repeat steps 3-8
11. merge in any changes to main
    1. git checkout main
    2. git pull
    3. git checkout \<feature_branch_name\>
    4. git rebase main
12. git push origin \<feature_branch_name\>
13. review or request review of changes in github
14. submit pull request in github


### Compiling requirements files

Requriements files must be compiled in the correct order to handle layering.

```
pip-compile requirements/requirements.in
pip-compile requirements/test-requirements.in
pip-compile requirements/dev-requirements.in
```
