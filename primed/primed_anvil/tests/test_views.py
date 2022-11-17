import json

from anvil_consortium_manager import models as acm_models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.http.response import Http404
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase
from django.urls import reverse

from primed.dbgap.tests.factories import (
    dbGaPStudyAccessionFactory,
    dbGaPWorkspaceFactory,
)

from .. import models, views
from . import factories

# from .utils import AnVILAPIMockTestMixin

User = get_user_model()


class StudyDetailTest(TestCase):
    """Tests for the StudyDetail view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.StudyFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("primed_anvil:studies:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.StudyDetail.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        obj = self.model_factory.create()
        request = self.factory.get(self.get_url(obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=obj.pk)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_view_status_code_with_invalid_pk(self):
        """Raises a 404 error with an invalid object pk."""
        obj = self.model_factory.create()
        request = self.factory.get(self.get_url(obj.pk + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, pk=obj.pk + 1)

    def test_dbgap_workspace_table(self):
        """Contains a table of dbGaPWorkspaces with the correct studies."""
        obj = self.model_factory.create()
        dbgap_study_accession = dbGaPStudyAccessionFactory.create(studies=[obj])
        dbgap_workspace = dbGaPWorkspaceFactory.create(
            dbgap_study_accession=dbgap_study_accession
        )
        other_workspace = dbGaPWorkspaceFactory.create()
        # import ipdb; ipdb.set_trace()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertIn("dbgap_workspace_table", response.context_data)
        table = response.context_data["dbgap_workspace_table"]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(dbgap_workspace.workspace, table.data)
        self.assertNotIn(other_workspace.workspace, table.data)


class StudyAutocompleteTest(TestCase):
    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with the correct permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("primed_anvil:studies:autocomplete", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.StudyAutocomplete.as_view()

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

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_returns_all_objects(self):
        """Queryset returns all objects when there is no query."""
        objects = factories.StudyFactory.create_batch(10)
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 10)
        self.assertEqual(
            sorted(returned_ids), sorted([object.pk for object in objects])
        )

    def test_returns_correct_object_match_short_name(self):
        """Queryset returns the correct objects when query matches the short_name."""
        object = factories.StudyFactory.create(
            short_name="test", full_name="other study"
        )
        request = self.factory.get(self.get_url(), {"q": "test"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_starting_with_query_short_name(self):
        """Queryset returns the correct objects when query matches the beginning of the short_name."""
        object = factories.StudyFactory.create(
            short_name="test", full_name="other study"
        )
        request = self.factory.get(self.get_url(), {"q": "test"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_containing_query_short_name(self):
        """Queryset returns the correct objects when the short_name contains the query."""
        object = factories.StudyFactory.create(
            short_name="test", full_name="other study"
        )
        request = self.factory.get(self.get_url(), {"q": "es"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_case_insensitive_short_name(self):
        """Queryset returns the correct objects when query matches the beginning of the short_name."""
        object = factories.StudyFactory.create(
            short_name="TEST", full_name="other study"
        )
        request = self.factory.get(self.get_url(), {"q": "test"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_match_full_name(self):
        """Queryset returns the correct objects when query matches the full_name."""
        object = factories.StudyFactory.create(
            short_name="other", full_name="test study"
        )
        request = self.factory.get(self.get_url(), {"q": "test study"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_starting_with_query_full_name(self):
        """Queryset returns the correct objects when query matches the beginning of the full_name."""
        object = factories.StudyFactory.create(
            short_name="other", full_name="test study"
        )
        request = self.factory.get(self.get_url(), {"q": "test"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_containing_query_full_name(self):
        """Queryset returns the correct objects when the full_name contains the query."""
        object = factories.StudyFactory.create(
            short_name="other", full_name="test study"
        )
        request = self.factory.get(self.get_url(), {"q": "stu"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_case_insensitive_full_name(self):
        """Queryset returns the correct objects when query matches the beginning of the full_name."""
        object = factories.StudyFactory.create(
            short_name="other", full_name="TEST STUDY"
        )
        request = self.factory.get(self.get_url(), {"q": "test study"})
        request.user = self.user
        response = self.get_view()(request)
        returned_ids = [
            int(x["id"])
            for x in json.loads(response.content.decode("utf-8"))["results"]
        ]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)


class StudyCreateTest(TestCase):
    """Tests for the StudyCreate view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.StudyFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("primed_anvil:studies:new", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.StudyCreate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url()
        )

    def test_status_code_with_user_permission_edit(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_access_without_user_permission_view(self):
        """Raises permission denied if user has no permissions."""
        user_view_perm = User.objects.create_user(
            username="test-none", password="test-none"
        )
        user_view_perm.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        request = self.factory.get(self.get_url())
        request.user = user_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_has_form_in_context(self):
        """Response includes a form."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertTrue("form" in response.context_data)

    def test_can_create_object(self):
        """Can create an object."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(), {"short_name": "TEST", "full_name": "Test study"}
        )
        self.assertEqual(response.status_code, 302)
        # A new object was created.
        self.assertEqual(models.Study.objects.count(), 1)
        new_object = models.Study.objects.latest("pk")
        self.assertEqual(new_object.short_name, "TEST")
        self.assertEqual(new_object.full_name, "Test study")

    def test_redirect_url(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(), {"short_name": "TEST", "full_name": "Test study"}
        )
        new_object = models.Study.objects.latest("pk")
        self.assertRedirects(response, new_object.get_absolute_url())

    def test_success_message(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {"short_name": "TEST", "full_name": "Test study"},
            follow=True,
        )
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(views.StudyCreate.success_msg, str(messages[0]))

    def test_error_missing_short_name(self):
        """Form shows an error when short name is missing."""
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"full_name": "Test study"})
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.Study.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("short_name", form.errors)
        self.assertEqual(len(form.errors["short_name"]), 1)
        self.assertIn("required", form.errors["short_name"][0])

    def test_error_missing_full_name(self):
        """Form shows an error when full name is missing."""
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"short_name": "TEST"})
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.Study.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("full_name", form.errors)
        self.assertEqual(len(form.errors["full_name"]), 1)
        self.assertIn("required", form.errors["full_name"][0])

    def test_error_duplicate_short_name(self):
        """Form shows an error when trying to create a duplicate short name."""
        factories.StudyFactory.create(short_name="TEST", full_name="Test study")
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(), {"short_name": "TEST", "full_name": "Test study 2"}
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.Study.objects.count(), 1)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("short_name", form.errors)
        self.assertEqual(len(form.errors["short_name"]), 1)
        self.assertIn("already exists", form.errors["short_name"][0])

    def test_post_blank_data(self):
        """Posting blank data does not create an object."""
        request = self.factory.post(self.get_url(), {})
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("short_name", form.errors.keys())
        self.assertEqual(len(form.errors["short_name"]), 1)
        self.assertIn("required", form.errors["short_name"][0])
        self.assertIn("full_name", form.errors.keys())
        self.assertEqual(len(form.errors["full_name"]), 1)
        self.assertIn("required", form.errors["full_name"][0])
        self.assertEqual(models.Study.objects.count(), 0)
