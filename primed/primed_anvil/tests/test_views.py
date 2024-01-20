import json

from anvil_consortium_manager import models as acm_models
from anvil_consortium_manager.tests.factories import AccountFactory
from anvil_consortium_manager.views import AccountList
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.http.response import Http404
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase
from django.urls import reverse

from primed.cdsa.tables import CDSAWorkspaceStaffTable, CDSAWorkspaceUserTable
from primed.cdsa.tests.factories import (
    CDSAWorkspaceFactory,
    DataAffiliateAgreementFactory,
    MemberAgreementFactory,
)
from primed.dbgap.tables import dbGaPWorkspaceStaffTable, dbGaPWorkspaceUserTable
from primed.dbgap.tests.factories import (
    dbGaPApplicationFactory,
    dbGaPStudyAccessionFactory,
    dbGaPWorkspaceFactory,
)
from primed.miscellaneous_workspaces.tables import (
    OpenAccessWorkspaceStaffTable,
    OpenAccessWorkspaceUserTable,
)
from primed.miscellaneous_workspaces.tests.factories import OpenAccessWorkspaceFactory
from primed.primed_anvil.tests.factories import AvailableDataFactory, StudyFactory
from primed.users.tests.factories import UserFactory

from .. import models, tables, views
from . import factories

# from .utils import AnVILAPIMockTestMixin

User = get_user_model()


class ACMNavbarTest(TestCase):
    """Tests for the ACM navbar."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.StudyFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:index", args=args)

    def test_staff_view_links(self):
        user = UserFactory.create()
        user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url())
        self.assertNotContains(response, reverse("primed_anvil:studies:new"))

    def test_staff_edit_links(self):
        user = UserFactory.create()
        user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url())
        self.assertContains(response, reverse("primed_anvil:studies:new"))


class HomeTest(TestCase):
    """Tests of the home page. This is maybe not the best place to put this test?"""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.StudyFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("home", args=args)

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url()
        )

    def test_status_code_logged_in(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_user_has_linked_account(self):
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertContains(response, reverse("anvil_consortium_manager:accounts:link"))

    def test_user_has_not_linked_account(self):
        self.client.force_login(self.user)
        AccountFactory.create(user=self.user, verified=True)
        response = self.client.get(self.get_url())
        self.assertNotContains(
            response, reverse("anvil_consortium_manager:accounts:link")
        )

    def test_staff_view_links(self):
        user = UserFactory.create()
        user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url())
        # Note: we need quotes around the link because anvil/accounts/link does appear in the response,
        # so we can't test if "anvil/" is in the response. We need to test if '"anvil/"' is in the response.
        self.assertContains(
            response, '"{}"'.format(reverse("anvil_consortium_manager:index"))
        )

    def test_view_links(self):
        user = UserFactory.create()
        user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url())
        # Note: we need quotes around the link because anvil/accounts/link does appear in the response,
        # so we can't test if "anvil/" is in the response. We need to test if '"anvil/"' is in the response.
        self.assertNotContains(
            response, '"{}"'.format(reverse("anvil_consortium_manager:index"))
        )


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
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
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

    def test_status_code_with_limited_view_permission(self):
        """Returns successful response code with user has limited view permission."""
        obj = self.model_factory.create()
        user = User.objects.create_user(username="test-2", password="test-2")
        user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertEqual(response.status_code, 200)

    def test_content_staff_view_permission(self):
        obj = self.model_factory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertContains(response, "Date created")

    def test_content_view_permission(self):
        obj = self.model_factory.create()
        user = User.objects.create_user(username="test-2", password="test-2")
        user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertNotContains(response, "Date created")

    def test_table_classes_view_permission(self):
        obj = self.model_factory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertIn("tables", response.context_data)
        self.assertIsInstance(
            response.context_data["tables"][0], dbGaPWorkspaceStaffTable
        )
        self.assertIsInstance(
            response.context_data["tables"][1], CDSAWorkspaceStaffTable
        )
        self.assertIsInstance(
            response.context_data["tables"][3], OpenAccessWorkspaceStaffTable
        )

    def test_table_classes_limited_view_permission(self):
        """Table classes are correct when the user has limited view permission."""
        user = User.objects.create_user(username="test-2", password="test-2")
        user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        obj = self.model_factory.create()
        self.client.force_login(user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertIn("tables", response.context_data)
        self.assertIsInstance(
            response.context_data["tables"][0], dbGaPWorkspaceUserTable
        )
        self.assertIsInstance(
            response.context_data["tables"][1], CDSAWorkspaceUserTable
        )
        self.assertIsInstance(
            response.context_data["tables"][3], OpenAccessWorkspaceUserTable
        )

    def test_dbgap_workspace_table(self):
        """Contains a table of dbGaPWorkspaces with the correct studies."""
        obj = self.model_factory.create()
        dbgap_study_accession = dbGaPStudyAccessionFactory.create(studies=[obj])
        dbgap_workspace = dbGaPWorkspaceFactory.create(
            dbgap_study_accession=dbgap_study_accession
        )
        other_workspace = dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        table = response.context_data["tables"][0]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(dbgap_workspace.workspace, table.data)
        self.assertNotIn(other_workspace.workspace, table.data)

    def test_cdsa_workspace_table(self):
        """Contains a table of CDSAWorkspaces with the correct studies."""
        obj = self.model_factory.create()
        cdsa_workspace = CDSAWorkspaceFactory.create(study=obj)
        other_workspace = CDSAWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        table = response.context_data["tables"][1]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(cdsa_workspace.workspace, table.data)
        self.assertNotIn(other_workspace.workspace, table.data)

    def test_open_access_workspace_table(self):
        """Contains a table of OpenAccessWorkspaces with the correct studies."""
        obj = self.model_factory.create()
        open_access_workspace = OpenAccessWorkspaceFactory.create()
        open_access_workspace.studies.add(obj)
        other_workspace = OpenAccessWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        table = response.context_data["tables"][3]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(open_access_workspace.workspace, table.data)
        self.assertNotIn(other_workspace.workspace, table.data)

    def test_cdsa_table(self):
        obj = self.model_factory.create()
        site_cdsa = DataAffiliateAgreementFactory.create(study=obj)
        other_cdsa = DataAffiliateAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertIn("tables", response.context_data)
        table = response.context_data["tables"][2]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(site_cdsa, table.data)
        self.assertNotIn(other_cdsa, table.data)


class StudyAutocompleteTest(TestCase):
    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with the correct permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
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

    def test_get_result_label(self):
        instance = factories.StudyFactory.create(
            full_name="Test Name", short_name="TEST"
        )
        request = self.factory.get(self.get_url())
        request.user = self.user
        view = views.StudyAutocomplete()
        view.setup(request)
        self.assertEqual(view.get_result_label(instance), "Test Name (TEST)")

    def test_get_selected_result_label(self):
        instance = factories.StudyFactory.create(
            full_name="Test Name", short_name="TEST"
        )
        request = self.factory.get(self.get_url())
        request.user = self.user
        view = views.StudyAutocomplete()
        view.setup(request)
        self.assertEqual(view.get_selected_result_label(instance), "TEST")


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
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
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
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
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
        self.assertEqual(views.StudyCreate.success_message, str(messages[0]))

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


class StudyListTest(TestCase):
    """Tests for the StudyList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.StudyFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self):
        """Get the url for the view being tested."""
        return reverse("primed_anvil:studies:list")

    def get_view(self):
        """Return the view being tested."""
        return views.StudyList.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url()
        )

    def test_view_render(self):
        obj = self.model_factory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())

        self.assertContains(response, obj.short_name)
        self.assertTemplateUsed(response, "primed_anvil/study_list.html")

    def test_status_code_with_view_permission(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_status_code_with_limited_view_permission(self):
        """Returns successful response code."""
        user = User.objects.create_user(username="test-2", password="test-2")
        user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url())
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

    def test_view_has_correct_table_class(self):
        """View has the correct table class in the context."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIn("table", response.context_data)
        self.assertIsInstance(response.context_data["table"], tables.StudyTable)

    def test_view_with_no_objects(self):
        """The table has no rows when there are no Study objects."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_view_with_one_object(self):
        """The table has one row when there is one Study object."""
        self.model_factory.create()
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 1)

    def test_view_with_two_objects(self):
        """The table has two rows when there are two Study objects."""
        self.model_factory.create_batch(2)
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 2)


class StudySiteDetailTest(TestCase):
    """Tests for the StudySiteDetail view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.StudySiteFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("primed_anvil:study_sites:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.StudySiteDetail.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1)
        )

    def test_view_render(self):
        obj = self.model_factory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertContains(response, obj.short_name)
        self.assertTemplateUsed(response, "primed_anvil/studysite_detail.html")

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

    def test_site_user_table(self):
        """Contains a table of site users with the correct users."""
        obj = self.model_factory.create()
        site_user = UserFactory.create()
        site_user.study_sites.set([obj])
        non_site_user = UserFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertIn("tables", response.context_data)
        table = response.context_data["tables"][0]
        self.assertEqual(len(table.rows), 1)

        self.assertIn(site_user, table.data)
        self.assertNotIn(non_site_user, table.data)

    def test_dbgap_table(self):
        obj = self.model_factory.create()
        site_application = dbGaPApplicationFactory.create()
        site_application.principal_investigator.study_sites.add(obj)
        other_application = dbGaPApplicationFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertIn("tables", response.context_data)
        table = response.context_data["tables"][1]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(site_application, table.data)
        self.assertNotIn(other_application, table.data)

    def test_cdsa_table(self):
        obj = self.model_factory.create()
        site_cdsa = MemberAgreementFactory.create(study_site=obj)
        other_cdsa = MemberAgreementFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertIn("tables", response.context_data)
        table = response.context_data["tables"][2]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(site_cdsa, table.data)
        self.assertNotIn(other_cdsa, table.data)


class StudySiteListTest(TestCase):
    """Tests for the StudySiteList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.StudySiteFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self):
        """Get the url for the view being tested."""
        return reverse("primed_anvil:study_sites:list")

    def get_view(self):
        """Return the view being tested."""
        return views.StudySiteList.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url()
        )

    def test_view_render(self):
        obj = self.model_factory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())

        self.assertContains(response, obj.short_name)
        self.assertTemplateUsed(response, "primed_anvil/studysite_list.html")

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

    def test_view_has_correct_table_class(self):
        """View has the correct table class in the context."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIn("table", response.context_data)
        self.assertIsInstance(response.context_data["table"], tables.StudySiteTable)

    def test_view_with_no_objects(self):
        """The table has no rows when there are no StudySite objects."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_view_with_one_object(self):
        """The table has one row when there is one StudySite object."""
        self.model_factory.create()
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 1)

    def test_view_with_two_objects(self):
        """The table has two rows when there are two StudySite objects."""
        self.model_factory.create_batch(2)
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 2)


class AccountListTest(TestCase):
    """Tests for the AccountList view using the custom table."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = AccountFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:accounts:list")

    def get_view(self):
        """Return the view being tested."""
        return AccountList.as_view()

    def test_view_has_correct_table_class(self):
        """View has the correct table class in the context."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIn("table", response.context_data)
        self.assertIsInstance(response.context_data["table"], tables.AccountTable)

    def test_view_with_two_objects(self):
        """The table has two rows when there are two Account objects."""
        self.model_factory.create_batch(2)
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 2)

    def test_filter_by_name(self):
        """Filtering by name works as expected."""
        user = UserFactory.create(name="First Last")
        account = AccountFactory.create(user=user)
        other_account = AccountFactory.create(verified=True)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("anvil_consortium_manager:accounts:list"),
            {"user__name__icontains": "First"},
        )
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 1)
        self.assertIn(account, response.context_data["table"].data)
        self.assertNotIn(other_account, response.context_data["table"].data)


class AvailableDataTest(TestCase):
    """Tests for the StudyDetail view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.AvailableDataFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("primed_anvil:available_data:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.AvailableDataDetail.as_view()

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
        dbgap_workspace = dbGaPWorkspaceFactory.create()
        dbgap_workspace.available_data.add(obj)
        other_workspace = dbGaPWorkspaceFactory.create()
        # import ipdb; ipdb.set_trace()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(obj.pk))
        self.assertIn("dbgap_workspace_table", response.context_data)
        table = response.context_data["dbgap_workspace_table"]
        self.assertEqual(len(table.rows), 1)
        self.assertIn(dbgap_workspace.workspace, table.data)
        self.assertNotIn(other_workspace.workspace, table.data)


class DataSummaryTableTest(TestCase):
    """Tests for the DataSummaryTable view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        # Need at least one AvailableData for the view to work.
        self.available_data = AvailableDataFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("primed_anvil:summaries:data", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.DataSummaryView.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url()
        )

    def test_status_code_with_authenticated_user(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_table_class(self):
        """A summary table exists."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("summary_table", response.context_data)
        self.assertIsInstance(
            response.context_data["summary_table"], tables.DataSummaryTable
        )

    def test_table_rows(self):
        """A summary table exists."""
        # One open access workspace with one study, with one available data type.
        # One dbGaP workspae with two studies.
        study_1 = StudyFactory.create()
        open_workspace = OpenAccessWorkspaceFactory.create()
        open_workspace.studies.add(study_1)
        open_workspace.available_data.add(self.available_data)
        study_2 = StudyFactory.create()
        study_3 = StudyFactory.create()
        dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study_2, study_3])
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("summary_table", response.context_data)
        self.assertEqual(len(response.context_data["summary_table"].rows), 2)
