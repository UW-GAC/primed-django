import json

import pytest
from anvil_consortium_manager.models import AnVILProjectManagerAccess
from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    UserEmailEntryFactory,
)
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase
from django.urls import reverse

from primed.primed_anvil.tests.factories import StudySiteFactory
from primed.users.forms import UserChangeForm
from primed.users.models import User
from primed.users.tests.factories import UserFactory
from primed.users.views import (
    UserAutocompleteView,
    UserRedirectView,
    UserUpdateView,
    user_detail_view,
)

pytestmark = pytest.mark.django_db


class TestUserUpdateView:
    """
    TODO:
        extracting view initialization code as class-scoped fixture
        would be great if only pytest-django supported non-function-scoped
        fixture db access -- this is a work-in-progress for now:
        https://github.com/pytest-dev/pytest-django/pull/258
    """

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test_get_success_url(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_success_url() == f"/users/{user.username}/"

    def test_get_object(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_object() == user

    def test_authenticated(self, client, user: User, rf: RequestFactory):
        client.force_login(user)
        user_update_url = reverse("users:update")
        response = client.get(user_update_url)

        assert response.status_code == 200

    def test_not_authenticated(self, client):
        user_update_url = reverse("users:update")
        response = client.get(user_update_url)

        assert response.status_code == 302

    def test_form_valid(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        request.user = user

        view.request = request

        # Initialize the form
        form = UserChangeForm()
        form.cleaned_data = dict()
        view.form_valid(form)

        messages_sent = [m.message for m in messages.get_messages(request)]
        assert messages_sent == ["Information successfully updated"]


class TestUserRedirectView:
    def test_get_redirect_url(self, user: User, rf: RequestFactory):
        view = UserRedirectView()
        request = rf.get("/fake-url")
        request.user = user

        view.request = request

        assert view.get_redirect_url() == f"/users/{user.username}/"


class TestUserDetailView:
    def test_authenticated(self, client, user: User, rf: RequestFactory):
        client.force_login(user)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)

        assert response.status_code == 200

    def test_authenticated_with_verified_account(
        self, client, user: User, rf: RequestFactory
    ):
        client.force_login(user)
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        AccountFactory.create(email="foo@bar.com", user=user, verified=True)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)

        assert response.status_code == 200

    def test_authenticated_with_user_email_entry(
        self, client, user: User, rf: RequestFactory
    ):
        client.force_login(user)
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        UserEmailEntryFactory.create(email="foo@bar.com", user=user)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)

        assert response.status_code == 200

    def test_authenticated_with_unverified_account(
        self, client, user: User, rf: RequestFactory
    ):
        client.force_login(user)
        AccountFactory.create(email="foo@bar.com", user=user, verified=False)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)

        assert response.status_code == 200

    def test_authenticated_with_study_sites(
        self, client, user: User, rf: RequestFactory
    ):
        client.force_login(user)
        study_site = StudySiteFactory.create()
        user.study_sites.add(study_site)
        user_detail_url = reverse("users:detail", kwargs=dict(username=user.username))
        response = client.get(user_detail_url)

        assert response.status_code == 200

    def test_not_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = AnonymousUser()

        response = user_detail_view(request, username=user.username)
        login_url = reverse(settings.LOGIN_URL)

        assert response.status_code == 302
        assert response["Location"] == f"{login_url}?next=/fake-url/"


class UserAutocompleteTest(TestCase):
    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with the correct permissions.
        self.user = User.objects.create_user(username="test", password="test")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("users:autocomplete", args=args)

    def get_view(self):
        """Return the view being tested."""
        return UserAutocompleteView.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url()
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_returns_all_instances(self):
        """Queryset returns all instances when there is no query."""
        UserFactory.create_batch(9)
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        # The test user plus the ones we created in this test.
        self.assertEqual(len(returned_ids), 10)
        self.assertEqual(
            sorted(returned_ids),
            sorted([instance.pk for instance in User.objects.all()]),
        )

    def test_returns_correct_instance_match_name(self):
        """Queryset returns the correct instances when query matches the short_name."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "First Last"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_starting_with_query_name(self):
        """Queryset returns the correct instances when query matches the beginning of the short_name."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "Firs"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_containing_query_short_name(self):
        """Queryset returns the correct instances when the short_name contains the query."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "ast"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_case_insensitive_name(self):
        """Queryset returns the correct instances when query matches the beginning of the short_name."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "first last"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_match_email(self):
        """Queryset returns the correct instances when query matches the email."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "foo@bar.com"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_starting_with_query_email(self):
        """Queryset returns the correct instances when query matches the beginning of the email."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "foo"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_containing_query_email(self):
        """Queryset returns the correct instances when the email contains the query."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "bar"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_returns_correct_instance_case_insensitive_email(self):
        """Queryset returns the correct instances when query matches the beginning of the email."""
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url(), {"q": "FOO@BAR.COM"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], instance.pk)

    def test_get_result_label(self):
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url())
        request.user = self.user
        view = UserAutocompleteView()
        view.setup(request)
        self.assertEqual(view.get_result_label(instance), "First Last (foo@bar.com)")

    def test_get_selected_result_label(self):
        instance = UserFactory.create(email="foo@bar.com", name="First Last")
        UserFactory.create(email="test@example.com", name="Other Name")
        request = self.factory.get(self.get_url())
        request.user = self.user
        view = UserAutocompleteView()
        view.setup(request)
        self.assertEqual(
            view.get_selected_result_label(instance), "First Last (foo@bar.com)"
        )
