"""Tests for views related to the `dbgap` app."""

import json
from datetime import timedelta

import responses
from anvil_consortium_manager import views as acm_views
from anvil_consortium_manager.models import (
    AnVILProjectManagerAccess,
    GroupGroupMembership,
    ManagedGroup,
    Workspace,
)
from anvil_consortium_manager.tests.api_factories import ErrorResponseFactory
from anvil_consortium_manager.tests.factories import (
    BillingProjectFactory,
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
)
from anvil_consortium_manager.tests.utils import AnVILAPIMockTestMixin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from faker import Faker
from freezegun import freeze_time

from primed.duo.tests.factories import DataUseModifierFactory, DataUsePermissionFactory
from primed.miscellaneous_workspaces.tables import DataPrepWorkspaceUserTable
from primed.miscellaneous_workspaces.tests.factories import DataPrepWorkspaceFactory
from primed.primed_anvil.tests.factories import (  # DataUseModifierFactory,; DataUsePermissionFactory,
    StudyFactory,
)
from primed.users.tests.factories import UserFactory

from .. import audit, constants, forms, models, tables, views
from . import factories

fake = Faker()

User = get_user_model()


class dbGaPResponseTestMixin:
    """Test mixin to help mock responses from dbGaP urls."""

    def setUp(self):
        super().setUp()
        self.dbgap_response_mock = responses.RequestsMock(assert_all_requests_are_fired=True)
        self.dbgap_response_mock.start()

    def tearDown(self):
        super().tearDown()
        self.dbgap_response_mock.stop()
        self.dbgap_response_mock.reset()


class NavbarTest(TestCase):
    """Tests for the navbar involving CDSA links."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:index", args=args)

    def test_links_for_staff_view(self):
        """Returns successful response code."""
        user = User.objects.create_user(username="test", password="test")
        user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url())
        self.assertContains(response, reverse("dbgap:dbgap_study_accessions:list"))
        self.assertContains(response, reverse("dbgap:dbgap_applications:list"))
        # Links to add dbGaP info.
        self.assertNotContains(response, reverse("dbgap:dbgap_study_accessions:new"))
        self.assertNotContains(response, reverse("dbgap:dbgap_applications:new"))
        self.assertNotContains(response, reverse("dbgap:dbgap_applications:update_dars"))

    def test_links_for_staff_edit(self):
        """Returns successful response code."""
        user = User.objects.create_user(username="test", password="test")
        user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME)
        )
        self.client.force_login(user)
        response = self.client.get(self.get_url())
        self.assertContains(response, reverse("dbgap:dbgap_study_accessions:list"))
        self.assertContains(response, reverse("dbgap:dbgap_applications:list"))
        # Links to add dbGaP info.
        self.assertContains(response, reverse("dbgap:dbgap_study_accessions:new"))
        self.assertContains(response, reverse("dbgap:dbgap_applications:new"))
        self.assertContains(response, reverse("dbgap:dbgap_applications:update_dars"))


class dbGaPStudyAccessionListTest(TestCase):
    """Tests for the dbGaPStudyAccessionList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:dbgap_study_accessions:list", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPStudyAccessionList.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_table_class(self):
        """The table is the correct class."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIn("table", response.context_data)
        self.assertIsInstance(response.context_data["table"], tables.dbGaPStudyAccessionTable)

    def test_workspace_table_none(self):
        """No rows are shown if there are no dbGaPStudyAccession objects."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_workspace_table_one(self):
        """One row is shown if there is one dbGaPStudyAccession."""
        factories.dbGaPStudyAccessionFactory.create()
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 1)

    def test_workspace_table_two(self):
        """Two rows are shown if there are two dbGaPStudyAccession objects."""
        factories.dbGaPStudyAccessionFactory.create_batch(2)
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 2)


class dbGaPStudyAccessionDetailTest(TestCase):
    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        # Create an object test this with.
        self.obj = factories.dbGaPStudyAccessionFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:dbgap_study_accessions:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPStudyAccessionDetail.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(self.obj.dbgap_phs))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(self.obj.dbgap_phs),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url(self.obj.dbgap_phs))
        request.user = self.user
        response = self.get_view()(request, dbgap_phs=self.obj.dbgap_phs)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url(self.obj.dbgap_phs))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, dbgap_phs=self.obj.dbgap_phs)

    def test_view_status_code_with_existing_object(self):
        """Returns a successful status code for an existing object pk."""
        # Only clients load the template.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.dbgap_phs))
        self.assertEqual(response.status_code, 200)

    def test_view_status_code_with_invalid_pk(self):
        """Raises a 404 error with an invalid object pk."""
        request = self.factory.get(self.get_url(self.obj.dbgap_phs + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, pk=self.obj.dbgap_phs + 1)

    def test_workspace_table(self):
        """The workspace table exists."""
        request = self.factory.get(self.get_url(self.obj.dbgap_phs))
        request.user = self.user
        response = self.get_view()(request, dbgap_phs=self.obj.dbgap_phs)
        self.assertIn("workspace_table", response.context_data)
        self.assertIsInstance(response.context_data["workspace_table"], tables.dbGaPWorkspaceStaffTable)

    def test_workspace_table_none(self):
        """No workspaces are shown if the dbGaPStudyAccession does not have any workspaces."""
        request = self.factory.get(self.get_url(self.obj.dbgap_phs))
        request.user = self.user
        response = self.get_view()(request, dbgap_phs=self.obj.dbgap_phs)
        self.assertIn("workspace_table", response.context_data)
        self.assertEqual(len(response.context_data["workspace_table"].rows), 0)

    def test_workspace_table_one(self):
        """One workspace is shown if the dbGaPStudyAccession has one workspace."""
        factories.dbGaPWorkspaceFactory.create(dbgap_study_accession=self.obj)
        request = self.factory.get(self.get_url(self.obj.dbgap_phs))
        request.user = self.user
        response = self.get_view()(request, dbgap_phs=self.obj.dbgap_phs)
        self.assertIn("workspace_table", response.context_data)
        self.assertEqual(len(response.context_data["workspace_table"].rows), 1)

    def test_workspace_table_two(self):
        """Two workspaces are shown if the dbGaPStudyAccession has two workspaces."""
        factories.dbGaPWorkspaceFactory.create_batch(2, dbgap_study_accession=self.obj)
        request = self.factory.get(self.get_url(self.obj.dbgap_phs))
        request.user = self.user
        response = self.get_view()(request, dbgap_phs=self.obj.dbgap_phs)
        self.assertIn("workspace_table", response.context_data)
        self.assertEqual(len(response.context_data["workspace_table"].rows), 2)

    def test_shows_workspace_for_only_this_dbGaPStudyAccession(self):
        """Only shows workspaces for this dbGaPStudyAccession."""
        other_dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        factories.dbGaPWorkspaceFactory.create(dbgap_study_accession=other_dbgap_study_accession)
        request = self.factory.get(self.get_url(self.obj.dbgap_phs))
        request.user = self.user
        response = self.get_view()(request, dbgap_phs=self.obj.dbgap_phs)
        self.assertIn("workspace_table", response.context_data)
        self.assertEqual(len(response.context_data["workspace_table"].rows), 0)

    def test_context_show_edit_links_with_edit_permission(self):
        edit_user = User.objects.create_user(username="edit", password="test")
        edit_user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME),
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME),
        )
        self.client.force_login(edit_user)
        account = factories.dbGaPStudyAccessionFactory.create()
        response = self.client.get(self.get_url(account.dbgap_phs))
        self.assertIn("show_edit_links", response.context_data)
        self.assertTrue(response.context_data["show_edit_links"])
        self.assertContains(
            response,
            reverse(
                "dbgap:dbgap_study_accessions:update",
                kwargs={"dbgap_phs": account.dbgap_phs},
            ),
        )

    def test_context_show_edit_links_with_view_permission(self):
        view_user = User.objects.create_user(username="edit", password="test")
        view_user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME),
        )
        self.client.force_login(view_user)
        account = factories.dbGaPStudyAccessionFactory.create()
        response = self.client.get(self.get_url(account.dbgap_phs))
        self.assertIn("show_edit_links", response.context_data)
        self.assertFalse(response.context_data["show_edit_links"])
        self.assertNotContains(
            response,
            reverse(
                "dbgap:dbgap_study_accessions:update",
                kwargs={"dbgap_phs": account.dbgap_phs},
            ),
        )


class dbGaPStudyAccessionCreateTest(TestCase):
    """Tests for the dbGaPStudyAccessionCreate view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.StudyFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME)
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:dbgap_study_accessions:new", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPStudyAccessionCreate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url())

    def test_status_code_with_user_permission_edit(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_access_without_user_permission_view(self):
        """Raises permission denied if user has no permissions."""
        user_view_perm = User.objects.create_user(username="test-none", password="test-none")
        user_view_perm.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
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

    def test_form_class(self):
        """Form is the expected class."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIsInstance(response.context_data["form"], forms.dbGaPStudyAccessionForm)

    def test_can_create_object(self):
        """Can create an object."""
        self.client.force_login(self.user)
        study = StudyFactory.create()
        response = self.client.post(self.get_url(), {"studies": [study.pk], "dbgap_phs": 1})
        self.assertEqual(response.status_code, 302)
        # A new object was created.
        self.assertEqual(models.dbGaPStudyAccession.objects.count(), 1)
        new_object = models.dbGaPStudyAccession.objects.latest("pk")
        self.assertEqual(new_object.studies.count(), 1)
        self.assertIn(study, new_object.studies.all())
        self.assertEqual(new_object.dbgap_phs, 1)

    def test_redirect_url(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        study = StudyFactory.create()
        response = self.client.post(self.get_url(), {"studies": [study.pk], "dbgap_phs": 1})
        new_object = models.dbGaPStudyAccession.objects.latest("pk")
        self.assertRedirects(response, new_object.get_absolute_url())

    def test_success_message(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {"studies": [study.pk], "dbgap_phs": 1},
            follow=True,
        )
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(views.dbGaPStudyAccessionCreate.success_message, str(messages[0]))

    def test_error_missing_studies(self):
        """Form shows an error when studies is missing."""
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"dbgap_phs": 1})
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPStudyAccession.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("studies", form.errors)
        self.assertEqual(len(form.errors["studies"]), 1)
        self.assertIn("required", form.errors["studies"][0])

    def test_error_missing_dbgap_phs(self):
        """Form shows an error when dbgap_phs is missing."""
        self.client.force_login(self.user)
        study = StudyFactory.create()
        response = self.client.post(self.get_url(), {"studies": [study.pk]})
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPStudyAccession.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_phs", form.errors)
        self.assertEqual(len(form.errors["dbgap_phs"]), 1)
        self.assertIn("required", form.errors["dbgap_phs"][0])

    def test_error_duplicate_short_name(self):
        """Form shows an error when trying to create a duplicate dbgap_phs."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        other_study = factories.StudyFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {"dbgap_phs": dbgap_study_accession.dbgap_phs, "studies": [other_study.pk]},
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPStudyAccession.objects.count(), 1)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_phs", form.errors)
        self.assertEqual(len(form.errors["dbgap_phs"]), 1)
        self.assertIn("already exists", form.errors["dbgap_phs"][0])

    def test_post_blank_data(self):
        """Posting blank data does not create an object."""
        request = self.factory.post(self.get_url(), {})
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 2)
        self.assertIn("studies", form.errors.keys())
        self.assertEqual(len(form.errors["studies"]), 1)
        self.assertIn("required", form.errors["studies"][0])
        self.assertIn("dbgap_phs", form.errors.keys())
        self.assertEqual(len(form.errors["dbgap_phs"]), 1)
        self.assertIn("required", form.errors["dbgap_phs"][0])
        self.assertEqual(models.dbGaPStudyAccession.objects.count(), 0)


class dbGaPStudyAccessionUpdateTest(TestCase):
    """Tests for the dbGaPStudyAccessionUpdate view."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME)
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:dbgap_study_accessions:update", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPStudyAccessionUpdate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        response = self.client.get(self.get_url(1))
        self.assertRedirects(response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1))

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        instance = factories.dbGaPStudyAccessionFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.dbgap_phs))
        self.assertEqual(response.status_code, 200)

    def test_access_with_view_permission(self):
        """Raises permission denied if user has only view permission."""
        instance = factories.dbGaPStudyAccessionFactory.create()
        user_with_view_perm = User.objects.create_user(username="test-other", password="test-other")
        user_with_view_perm.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        request = self.factory.get(self.get_url(instance.dbgap_phs))
        request.user = user_with_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, dbgap_phs=instance.dbgap_phs)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        instance = factories.dbGaPStudyAccessionFactory.create()
        user_no_perms = User.objects.create_user(username="test-other", password="test-other")
        request = self.factory.get(self.get_url(instance.dbgap_phs))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, dbgap_phs=instance.dbgap_phs)

    def test_object_does_not_exist(self):
        """Raises Http404 if object does not exist."""
        request = self.factory.get(self.get_url(1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, dbgap_phs=1)

    def test_has_form_in_context(self):
        """Response includes a form."""
        instance = factories.dbGaPStudyAccessionFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.dbgap_phs))
        self.assertTrue("form" in response.context_data)

    def test_can_modify_studies(self):
        """Can modify studies when updating a dbGaPStudyAccession."""
        study_1 = StudyFactory.create()
        study_2 = StudyFactory.create()
        instance = factories.dbGaPStudyAccessionFactory.create(studies=[study_1])
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(instance.dbgap_phs), {"studies": [study_1.pk, study_2.pk]})
        self.assertEqual(response.status_code, 302)
        instance.refresh_from_db()
        self.assertEqual(instance.studies.count(), 2)
        self.assertIn(study_1, instance.studies.all())
        self.assertIn(study_2, instance.studies.all())

    def test_does_not_modify_phs(self):
        """Does not modify phs when updating a dbGaPStudyAccession."""
        study = StudyFactory.create()
        instance = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=1234, studies=[study])
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(instance.dbgap_phs), {"dbgap_phs": 2345, "studies": [study.pk]})
        self.assertEqual(response.status_code, 302)
        instance.refresh_from_db()
        self.assertEqual(instance.dbgap_phs, 1234)

    def test_success_message(self):
        """Response includes a success message if successful."""
        study = StudyFactory.create()
        instance = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=1234, studies=[study])
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(instance.dbgap_phs), {"studies": [study.pk]}, follow=True)
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(views.dbGaPStudyAccessionUpdate.success_message, str(messages[0]))

    def test_redirects_to_object_detail(self):
        """After successfully creating an object, view redirects to the object's detail page."""
        study = StudyFactory.create()
        instance = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=1234, studies=[study])
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(instance.dbgap_phs), {"studies": [study.pk]})
        self.assertRedirects(response, instance.get_absolute_url())


class dbGaPStudyAccessionAutocompleteTest(TestCase):
    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with the correct permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:dbgap_study_accessions:autocomplete", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPStudyAccessionAutocomplete.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url())

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_returns_all_objects(self):
        """Queryset returns all objects when there is no query."""
        objects = factories.dbGaPStudyAccessionFactory.create_batch(10)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 10)
        self.assertEqual(sorted(returned_ids), sorted([object.pk for object in objects]))

    def test_returns_correct_object_match(self):
        """Queryset returns the correct objects when query matches the phs."""
        object = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=7)
        factories.dbGaPStudyAccessionFactory.create(dbgap_phs=8)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(), {"q": "7"})
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_starting_with_query(self):
        """Queryset returns the correct objects when query matches the beginning of the dbgap_phs."""
        object = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=765)
        factories.dbGaPStudyAccessionFactory.create(dbgap_phs=8)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(), {"q": "7"})
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_returns_correct_object_containing_query(self):
        """Queryset returns the correct objects when the dbgap_phs contains the query."""
        object = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=765)
        factories.dbGaPStudyAccessionFactory.create(dbgap_phs=754)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(), {"q": "6"})
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_ignores_phs_in_query(self):
        """get_queryset ignores "phs" in the query string."""
        object = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=7)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(), {"q": "phs7"})
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_removes_leading_zeros(self):
        """get_queryset ignores "phs" in the query string."""
        object = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=7)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(), {"q": "0007"})
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)

    def test_does_not_remove_trailing_zeros(self):
        """get_queryset ignores "phs" in the query string."""
        object = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=700)
        factories.dbGaPStudyAccessionFactory.create(dbgap_phs=71)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(), {"q": "700"})
        returned_ids = [int(x["id"]) for x in json.loads(response.content.decode("utf-8"))["results"]]
        self.assertEqual(len(returned_ids), 1)
        self.assertEqual(returned_ids[0], object.pk)


class dbGaPWorkspaceListTest(TestCase):
    """Tests of the anvil_consortium_manager WorkspaceList view using this app's dbGaPWorkspaceAdapter."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.workspace_type = "dbgap"

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:workspaces:list", args=args)

    def get_view(self):
        """Return the view being tested."""
        return acm_views.WorkspaceListByType.as_view()

    def test_view_has_correct_table_class(self):
        """The view has the correct table class in the context."""
        request = self.factory.get(self.get_url(self.workspace_type))
        request.user = self.user
        response = self.get_view()(request, workspace_type=self.workspace_type)
        self.assertIn("table", response.context_data)
        self.assertIsInstance(response.context_data["table"], tables.dbGaPWorkspaceStaffTable)


class dbGaPWorkspaceDetailTest(TestCase):
    """Tests of the WorkspaceDetail view from ACM with this app's dbGaPWorkspace model."""

    def setUp(self):
        """Set up test class."""
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        obj = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_shows_disease_term_if_required_by_duo_permission(self):
        """Displays the disease term if required by the DUO permission."""
        permission = DataUsePermissionFactory.create(requires_disease_term=True)
        obj = factories.dbGaPWorkspaceFactory.create(
            data_use_permission=permission,
            disease_term="MONDO:0000045",
        )
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertContains(response, "(Term: MONDO:0000045)")

    def test_does_not_show_disease_term_if_not_required_by_duo_permission(self):
        """Does not display a disease term or parentheses if a disease term is not required by the DUO permission."""
        permission = DataUsePermissionFactory.create()
        obj = factories.dbGaPWorkspaceFactory.create(
            data_use_permission=permission,
        )
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertNotContains(response, "(Term:")

    def test_response_contains_dbgap_link(self):
        """Response contains the link to the dbGaP page."""
        permission = DataUsePermissionFactory.create()
        obj = factories.dbGaPWorkspaceFactory.create(
            data_use_permission=permission,
        )
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertContains(response, obj.get_dbgap_link())

    def test_links_audit_access_staff_view(self):
        user = UserFactory.create()
        user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        obj = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(user)
        response = self.client.get(obj.get_absolute_url())
        self.assertContains(
            response,
            reverse(
                "dbgap:audit:workspaces",
                args=[obj.workspace.billing_project.name, obj.workspace.name],
            ),
        )

    def test_links_audit_access_view_permission(self):
        user = UserFactory.create()
        user.user_permissions.add(Permission.objects.get(codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME))
        obj = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(user)
        response = self.client.get(obj.get_absolute_url())
        self.assertNotContains(
            response,
            reverse(
                "dbgap:audit:workspaces",
                args=[obj.workspace.billing_project.name, obj.workspace.name],
            ),
        )

    def test_associated_data_prep_view_user(self):
        """View users do not see the associated data prep section"""
        user = User.objects.create_user(username="test-view", password="test-view")
        user.user_permissions.add(Permission.objects.get(codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME))

        obj = factories.dbGaPWorkspaceFactory.create()
        DataPrepWorkspaceFactory.create(target_workspace=obj.workspace)
        self.client.force_login(user)
        response = self.client.get(obj.get_absolute_url())
        self.assertNotContains(response, "Associated data prep workspaces")

    def test_associated_data_prep_staff_view_user(self):
        """Staff view users do see the associated data prep section."""
        obj = factories.dbGaPWorkspaceFactory.create()
        DataPrepWorkspaceFactory.create(target_workspace=obj.workspace)
        self.client.force_login(self.user)
        response = self.client.get(obj.get_absolute_url())
        self.assertContains(response, "Associated data prep workspaces")

    def test_associated_data_prep_workspaces_context_exists(self):
        obj = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.get_absolute_url())
        self.assertIn("associated_data_prep_workspaces", response.context_data)
        self.assertIsInstance(
            response.context_data["associated_data_prep_workspaces"],
            DataPrepWorkspaceUserTable,
        )

    def test_only_show_one_associated_data_prep_workspace(self):
        dbGaP_obj = factories.dbGaPWorkspaceFactory.create()
        dataPrep_obj = DataPrepWorkspaceFactory.create(target_workspace=dbGaP_obj.workspace)
        self.client.force_login(self.user)
        response = self.client.get(dbGaP_obj.get_absolute_url())
        self.assertIn("associated_data_prep_workspaces", response.context_data)
        self.assertEqual(len(response.context_data["associated_data_prep_workspaces"].rows), 1)
        self.assertIn(
            dataPrep_obj.workspace,
            response.context_data["associated_data_prep_workspaces"].data,
        )

    def test_show_two_associated_data_prep_workspaces(self):
        dbGaP_obj = factories.dbGaPWorkspaceFactory.create()
        dataPrep_obj1 = DataPrepWorkspaceFactory.create(target_workspace=dbGaP_obj.workspace)
        dataPrep_obj2 = DataPrepWorkspaceFactory.create(target_workspace=dbGaP_obj.workspace)
        self.client.force_login(self.user)
        response = self.client.get(dbGaP_obj.get_absolute_url())
        self.assertIn("associated_data_prep_workspaces", response.context_data)
        self.assertEqual(len(response.context_data["associated_data_prep_workspaces"].rows), 2)
        self.assertIn(
            dataPrep_obj1.workspace,
            response.context_data["associated_data_prep_workspaces"].data,
        )
        self.assertIn(
            dataPrep_obj2.workspace,
            response.context_data["associated_data_prep_workspaces"].data,
        )

    def test_context_data_prep_active_with_no_prep_workspace(self):
        instance = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(instance.get_absolute_url())
        self.assertIn("data_prep_active", response.context_data)
        self.assertFalse(response.context["data_prep_active"])

    def test_context_data_prep_active_with_one_inactive_prep_workspace(self):
        instance = factories.dbGaPWorkspaceFactory.create()
        DataPrepWorkspaceFactory.create(target_workspace=instance.workspace, is_active=False)
        self.client.force_login(self.user)
        response = self.client.get(instance.get_absolute_url())
        self.assertIn("data_prep_active", response.context_data)
        self.assertFalse(response.context["data_prep_active"])

    def test_context_data_prep_active_with_one_active_prep_workspace(self):
        instance = factories.dbGaPWorkspaceFactory.create()
        DataPrepWorkspaceFactory.create(target_workspace=instance.workspace, is_active=True)
        self.client.force_login(self.user)
        response = self.client.get(instance.get_absolute_url())
        self.assertIn("data_prep_active", response.context_data)
        self.assertTrue(response.context["data_prep_active"])

    def test_context_data_prep_active_with_one_active_one_inactive_prep_workspace(self):
        instance = factories.dbGaPWorkspaceFactory.create()
        DataPrepWorkspaceFactory.create(target_workspace=instance.workspace, is_active=True)
        DataPrepWorkspaceFactory.create(target_workspace=instance.workspace, is_active=True)
        self.client.force_login(self.user)
        response = self.client.get(instance.get_absolute_url())
        self.assertIn("data_prep_active", response.context_data)
        self.assertTrue(response.context["data_prep_active"])


class dbGaPWorkspaceCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceCreate view from ACM with this app's dbGaPWorkspace model."""

    api_success_code = 201

    def setUp(self):
        """Set up test class."""
        # The superclass uses the responses package to mock API responses.
        super().setUp()
        # Create a user with both view and edit permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME)
        )
        self.requester = UserFactory.create()
        self.workspace_type = "dbgap"

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:workspaces:new", args=args)

    def get_api_url(self, billing_project_name, workspace_name):
        """Return the Terra API url for a given billing project and workspace."""
        return self.api_client.rawls_entry_point + "/api/workspaces/" + billing_project_name + "/" + workspace_name

    def test_creates_upload_workspace_without_duos(self):
        """Posting valid data to the form creates a workspace data object when using a custom adapter."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        # Create an extra that won't be specified.
        DataUseModifierFactory.create()
        billing_project = BillingProjectFactory.create(name="test-billing-project")
        url = self.api_client.rawls_entry_point + "/api/workspaces"
        json_data = {
            "namespace": "test-billing-project",
            "name": "test-workspace",
            "attributes": {},
        }
        self.anvil_response_mock.add(
            responses.POST,
            url,
            status=self.api_success_code,
            match=[responses.matchers.json_params_matcher(json_data)],
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.workspace_type),
            {
                "billing_project": billing_project.pk,
                "name": "test-workspace",
                # Workspace data form.
                "workspacedata-TOTAL_FORMS": 1,
                "workspacedata-INITIAL_FORMS": 0,
                "workspacedata-MIN_NUM_FORMS": 1,
                "workspacedata-MAX_NUM_FORMS": 1,
                "workspacedata-0-dbgap_study_accession": dbgap_study_accession.pk,
                "workspacedata-0-dbgap_version": 2,
                "workspacedata-0-dbgap_participant_set": 3,
                "workspacedata-0-dbgap_consent_abbreviation": "GRU-TEST",
                "workspacedata-0-dbgap_consent_code": 4,
                "workspacedata-0-data_use_limitations": "test limitations",
                "workspacedata-0-acknowledgments": "test acknowledgments",
                "workspacedata-0-requested_by": self.requester.pk,
                "workspacedata-0-gsr_restricted": False,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.dbGaPWorkspace.objects.count(), 1)
        new_workspace_data = models.dbGaPWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(new_workspace_data.dbgap_study_accession, dbgap_study_accession)
        self.assertEqual(new_workspace_data.dbgap_version, 2)
        self.assertEqual(new_workspace_data.dbgap_participant_set, 3)
        self.assertEqual(new_workspace_data.dbgap_consent_abbreviation, "GRU-TEST")
        self.assertEqual(new_workspace_data.dbgap_consent_code, 4)
        self.assertEqual(new_workspace_data.data_use_limitations, "test limitations")
        self.assertEqual(new_workspace_data.acknowledgments, "test acknowledgments")
        self.assertEqual(new_workspace_data.requested_by, self.requester)

    def test_creates_upload_workspace_with_duos(self):
        """Posting valid data to the form creates a workspace data object when using a custom adapter."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        data_use_permission = DataUsePermissionFactory.create()
        data_use_modifier_1 = DataUseModifierFactory.create()
        data_use_modifier_2 = DataUseModifierFactory.create()
        # Create an extra that won't be specified.
        DataUseModifierFactory.create()
        billing_project = BillingProjectFactory.create(name="test-billing-project")
        url = self.api_client.rawls_entry_point + "/api/workspaces"
        json_data = {
            "namespace": "test-billing-project",
            "name": "test-workspace",
            "attributes": {},
        }
        self.anvil_response_mock.add(
            responses.POST,
            url,
            status=self.api_success_code,
            match=[responses.matchers.json_params_matcher(json_data)],
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.workspace_type),
            {
                "billing_project": billing_project.pk,
                "name": "test-workspace",
                # Workspace data form.
                "workspacedata-TOTAL_FORMS": 1,
                "workspacedata-INITIAL_FORMS": 0,
                "workspacedata-MIN_NUM_FORMS": 1,
                "workspacedata-MAX_NUM_FORMS": 1,
                "workspacedata-0-dbgap_study_accession": dbgap_study_accession.pk,
                "workspacedata-0-dbgap_version": 2,
                "workspacedata-0-dbgap_participant_set": 3,
                "workspacedata-0-dbgap_consent_abbreviation": "GRU-TEST",
                "workspacedata-0-dbgap_consent_code": 4,
                "workspacedata-0-data_use_limitations": "test limitations",
                "workspacedata-0-acknowledgments": "test acknowledgments",
                "workspacedata-0-data_use_permission": data_use_permission.pk,
                "workspacedata-0-data_use_modifiers": [
                    data_use_modifier_1.pk,
                    data_use_modifier_2.pk,
                ],
                "workspacedata-0-requested_by": self.requester.pk,
                "workspacedata-0-gsr_restricted": False,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_workspace_data = models.dbGaPWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.data_use_permission, data_use_permission)
        self.assertEqual(new_workspace_data.data_use_modifiers.count(), 2)
        self.assertIn(data_use_modifier_1, new_workspace_data.data_use_modifiers.all())
        self.assertIn(data_use_modifier_2, new_workspace_data.data_use_modifiers.all())


class dbGaPWorkspaceImportTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceImport view from ACM with this app's dbGaPWorkspace model."""

    api_success_code = 200

    def setUp(self):
        """Set up test class."""
        # The superclass uses the responses package to mock API responses.
        super().setUp()
        # Create a user with both view and edit permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME)
        )
        self.requester = UserFactory.create()
        self.workspace_type = "dbgap"

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:workspaces:import", args=args)

    def get_api_url(self, billing_project_name, workspace_name):
        """Return the Terra API url for a given billing project and workspace."""
        return self.api_client.rawls_entry_point + "/api/workspaces/" + billing_project_name + "/" + workspace_name

    def get_api_json_response(self, billing_project, workspace, authorization_domains=[], access="OWNER"):
        """Return a pared down version of the json response from the AnVIL API with only fields we need."""
        json_data = {
            "accessLevel": access,
            "owners": [],
            "workspace": {
                "authorizationDomain": [{"membersGroupName": x} for x in authorization_domains],
                "name": workspace,
                "namespace": billing_project,
                "isLocked": False,
            },
        }
        return json_data

    def test_creates_dbgap_workspace_without_duos(self):
        """Posting valid data to the form creates an UploadWorkspace object."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        # Create an extra that won't be specified.
        DataUseModifierFactory.create()
        billing_project = BillingProjectFactory.create(name="billing-project")
        workspace_name = "workspace"
        # Available workspaces API call.
        workspace_list_url = self.api_client.rawls_entry_point + "/api/workspaces"
        self.anvil_response_mock.add(
            responses.GET,
            workspace_list_url,
            match=[
                responses.matchers.query_param_matcher({"fields": "workspace.namespace,workspace.name,accessLevel"})
            ],
            status=200,
            json=[self.get_api_json_response(billing_project.name, workspace_name)],
        )
        url = self.get_api_url(billing_project.name, workspace_name)
        self.anvil_response_mock.add(
            responses.GET,
            url,
            status=self.api_success_code,
            json=self.get_api_json_response(billing_project.name, workspace_name),
        )
        # ACL API call.
        api_url_acl = (
            self.api_client.rawls_entry_point
            + "/api/workspaces/"
            + billing_project.name
            + "/"
            + workspace_name
            + "/acl"
        )
        self.anvil_response_mock.add(
            responses.GET,
            api_url_acl,
            status=200,
            json={
                "acl": {
                    self.service_account_email: {
                        "accessLevel": "OWNER",
                        "canCompute": True,
                        "canShare": True,
                        "pending": False,
                    }
                }
            },
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.workspace_type),
            {
                "workspace": billing_project.name + "/" + workspace_name,
                # Workspace data form.
                "workspacedata-TOTAL_FORMS": 1,
                "workspacedata-INITIAL_FORMS": 0,
                "workspacedata-MIN_NUM_FORMS": 1,
                "workspacedata-MAX_NUM_FORMS": 1,
                "workspacedata-0-dbgap_study_accession": dbgap_study_accession.pk,
                "workspacedata-0-dbgap_version": 2,
                "workspacedata-0-dbgap_participant_set": 3,
                "workspacedata-0-dbgap_consent_code": 4,
                "workspacedata-0-dbgap_consent_abbreviation": "GRU-TEST",
                "workspacedata-0-data_use_limitations": "test limitations",
                "workspacedata-0-acknowledgments": "test acknowledgments",
                "workspacedata-0-requested_by": self.requester.pk,
                "workspacedata-0-gsr_restricted": False,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.dbGaPWorkspace.objects.count(), 1)
        new_workspace_data = models.dbGaPWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(new_workspace_data.dbgap_study_accession, dbgap_study_accession)
        self.assertEqual(new_workspace_data.dbgap_version, 2)
        self.assertEqual(new_workspace_data.dbgap_participant_set, 3)
        self.assertEqual(new_workspace_data.dbgap_consent_abbreviation, "GRU-TEST")
        self.assertEqual(new_workspace_data.dbgap_consent_code, 4)
        self.assertEqual(new_workspace_data.data_use_limitations, "test limitations")
        self.assertEqual(new_workspace_data.acknowledgments, "test acknowledgments")
        self.assertEqual(new_workspace_data.requested_by, self.requester)

    def test_creates_dbgap_workspace_with_duos(self):
        """Posting valid data to the form creates an UploadWorkspace object."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        data_use_permission = DataUsePermissionFactory.create()
        data_use_modifier_1 = DataUseModifierFactory.create()
        data_use_modifier_2 = DataUseModifierFactory.create()
        # Create an extra that won't be specified.
        DataUseModifierFactory.create()
        billing_project = BillingProjectFactory.create(name="billing-project")
        workspace_name = "workspace"
        # Available workspaces API call.
        workspace_list_url = self.api_client.rawls_entry_point + "/api/workspaces"
        self.anvil_response_mock.add(
            responses.GET,
            workspace_list_url,
            match=[
                responses.matchers.query_param_matcher({"fields": "workspace.namespace,workspace.name,accessLevel"})
            ],
            status=200,
            json=[self.get_api_json_response(billing_project.name, workspace_name)],
        )
        url = self.get_api_url(billing_project.name, workspace_name)
        self.anvil_response_mock.add(
            responses.GET,
            url,
            status=self.api_success_code,
            json=self.get_api_json_response(billing_project.name, workspace_name),
        )
        # ACL API call.
        api_url_acl = (
            self.api_client.rawls_entry_point
            + "/api/workspaces/"
            + billing_project.name
            + "/"
            + workspace_name
            + "/acl"
        )
        self.anvil_response_mock.add(
            responses.GET,
            api_url_acl,
            status=200,
            json={
                "acl": {
                    self.service_account_email: {
                        "accessLevel": "OWNER",
                        "canCompute": True,
                        "canShare": True,
                        "pending": False,
                    }
                }
            },
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.workspace_type),
            {
                "workspace": billing_project.name + "/" + workspace_name,
                # Workspace data form.
                "workspacedata-TOTAL_FORMS": 1,
                "workspacedata-INITIAL_FORMS": 0,
                "workspacedata-MIN_NUM_FORMS": 1,
                "workspacedata-MAX_NUM_FORMS": 1,
                "workspacedata-0-dbgap_study_accession": dbgap_study_accession.pk,
                "workspacedata-0-dbgap_version": 2,
                "workspacedata-0-dbgap_participant_set": 3,
                "workspacedata-0-dbgap_consent_code": 4,
                "workspacedata-0-dbgap_consent_abbreviation": "GRU-TEST",
                "workspacedata-0-data_use_limitations": "test limitations",
                "workspacedata-0-acknowledgments": "test acknowledgments",
                "workspacedata-0-data_use_permission": data_use_permission.pk,
                "workspacedata-0-data_use_modifiers": [
                    data_use_modifier_1.pk,
                    data_use_modifier_2.pk,
                ],
                "workspacedata-0-requested_by": self.requester.pk,
                "workspacedata-0-gsr_restricted": False,
            },
        )
        self.assertEqual(response.status_code, 302)
        new_workspace_data = models.dbGaPWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.data_use_permission, data_use_permission)
        self.assertEqual(new_workspace_data.data_use_modifiers.count(), 2)
        self.assertIn(data_use_modifier_1, new_workspace_data.data_use_modifiers.all())
        self.assertIn(data_use_modifier_2, new_workspace_data.data_use_modifiers.all())


class dbGaPApplicationListTest(TestCase):
    """Tests for the dbGaPApplicationList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:dbgap_applications:list", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPApplicationList.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_table_class(self):
        """The table is the correct class."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIn("table", response.context_data)
        self.assertIsInstance(response.context_data["table"], tables.dbGaPApplicationTable)


class dbGaPApplicationDetailTest(TestCase):
    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        # Create an object test this with.
        self.obj = factories.dbGaPApplicationFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:dbgap_applications:detail", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPApplicationDetail.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(self.obj.dbgap_project_id))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(self.obj.dbgap_project_id),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.obj.dbgap_project_id)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, dbgap_project_id=self.obj.dbgap_project_id)

    def test_view_status_code_with_existing_object(self):
        """Returns a successful status code for an existing object pk."""
        # Only clients load the template.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.dbgap_project_id))
        self.assertEqual(response.status_code, 200)

    def test_view_status_code_with_invalid_pk(self):
        """Raises a 404 error with an invalid object pk."""
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, pk=self.obj.dbgap_project_id + 1)

    def test_staff_edit_links(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME)
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.dbgap_project_id))
        self.assertContains(
            response,
            reverse(
                "dbgap:dbgap_applications:dbgap_data_access_snapshots:new",
                args=[self.obj.dbgap_project_id],
            ),
        )
        self.assertContains(
            response,
            reverse("dbgap:audit:applications", args=[self.obj.dbgap_project_id]),
        )
        "dbgap:dbgap_applications:dbgap_data_access_snapshots:new"

    def test_staff_view_links(self):
        """No edit links if staff user only has view permission."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.dbgap_project_id))
        self.assertNotContains(
            response,
            reverse(
                "dbgap:dbgap_applications:dbgap_data_access_snapshots:new",
                args=[self.obj.dbgap_project_id],
            ),
        )
        self.assertContains(
            response,
            reverse("dbgap:audit:applications", args=[self.obj.dbgap_project_id]),
        )

    def test_context_snapshot_table(self):
        """The data_access_snapshot_table exists in the context."""
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.obj.dbgap_project_id)
        self.assertIn("data_access_snapshot_table", response.context_data)
        self.assertIsInstance(
            response.context_data["data_access_snapshot_table"],
            tables.dbGaPDataAccessSnapshotTable,
        )

    def test_snapshot_table_none(self):
        """No snapshots are shown if the dbGaPApplication has no snapshots."""
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.obj.dbgap_project_id)
        self.assertIn("data_access_snapshot_table", response.context_data)
        self.assertEqual(len(response.context_data["data_access_snapshot_table"].rows), 0)

    def test_snapshot_table_one(self):
        """One snapshots is shown if the dbGaPApplication has one snapshots."""
        factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=self.obj)
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.obj.dbgap_project_id)
        self.assertIn("data_access_snapshot_table", response.context_data)
        self.assertEqual(len(response.context_data["data_access_snapshot_table"].rows), 1)

    def test_snapshot_table_two(self):
        """Two snapshots are shown if the dbGaPApplication has two snapshots."""
        factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=self.obj, is_most_recent=False)
        factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=self.obj)
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.obj.dbgap_project_id)
        self.assertIn("data_access_snapshot_table", response.context_data)
        self.assertEqual(len(response.context_data["data_access_snapshot_table"].rows), 2)

    def test_shows_snapshots_for_only_this_application(self):
        """Only shows snapshots for this dbGaPApplication."""
        other_dbgap_application = factories.dbGaPApplicationFactory.create()
        factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=other_dbgap_application)
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.obj.dbgap_project_id)
        self.assertIn("data_access_snapshot_table", response.context_data)
        self.assertEqual(len(response.context_data["data_access_snapshot_table"].rows), 0)

    def test_context_latest_snapshot_no_snapshot(self):
        """latest_snapshot is None in context when there are no dbGaPDataAccessSnapshots for this application."""
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.obj.dbgap_project_id)
        self.assertIn("latest_snapshot", response.context_data)
        self.assertIsNone(response.context_data["latest_snapshot"])

    def test_context_latest_snapshot_one_snapshot(self):
        """latest_snapshot is correct in context when there is one dbGaPDataAccessSnapshot for this application."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=self.obj)
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.obj.dbgap_project_id)
        self.assertIn("latest_snapshot", response.context_data)
        self.assertEqual(response.context_data["latest_snapshot"], dbgap_snapshot)

    def test_context_latest_snapshot_two_snapshots(self):
        """latest_snapshot is correct in context when there are two dbGaPDataAccessSnapshots for this application."""
        factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=self.obj,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=False,
        )
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=self.obj, created=timezone.now()
        )
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.obj.dbgap_project_id)
        self.assertIn("latest_snapshot", response.context_data)
        self.assertEqual(response.context_data["latest_snapshot"], dbgap_snapshot)

    def test_table_default_ordering(self):
        """Most recent dbGaPDataAccessSnapshots appear first."""
        snapshot_1 = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=self.obj,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=False,
        )
        snapshot_2 = factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=self.obj, created=timezone.now())
        request = self.factory.get(self.get_url(self.obj.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.obj.dbgap_project_id)
        table = response.context_data["data_access_snapshot_table"]
        self.assertEqual(table.data[0], snapshot_2)
        self.assertEqual(table.data[1], snapshot_1)


class dbGaPApplicationCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests for the dbGaPApplication view."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        self.model_factory = factories.StudyFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME)
        )
        # Create the admin group.
        self.cc_admin_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:dbgap_applications:new", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPApplicationCreate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(response, resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url())

    def test_status_code_with_user_permission_edit(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_access_without_user_permission_view(self):
        """Raises permission denied if user has no permissions."""
        user_view_perm = User.objects.create_user(username="test-none", password="test-none")
        user_view_perm.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
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

    def test_form_class(self):
        """Form is the expected class."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIsInstance(response.context_data["form"], forms.dbGaPApplicationForm)

    def test_can_create_object(self):
        """Can create an object."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = self.api_client.sam_entry_point + "/api/groups/v1/TEST_PRIMED_DBGAP_ACCESS_1"
        self.anvil_response_mock.add(responses.POST, api_url, status=201, json={"message": "mock message"})
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point
            + "/api/groups/v1/TEST_PRIMED_DBGAP_ACCESS_1/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(self.get_url(), {"principal_investigator": pi.pk, "dbgap_project_id": 1})
        self.assertEqual(response.status_code, 302)
        # A new object was created.
        self.assertEqual(models.dbGaPApplication.objects.count(), 1)
        new_object = models.dbGaPApplication.objects.latest("pk")
        self.assertEqual(new_object.principal_investigator, pi)
        self.assertEqual(new_object.dbgap_project_id, 1)

    def test_redirect_url(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = self.api_client.sam_entry_point + "/api/groups/v1/TEST_PRIMED_DBGAP_ACCESS_1"
        self.anvil_response_mock.add(responses.POST, api_url, status=201, json={"message": "mock message"})
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            api_url + "/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(self.get_url(), {"principal_investigator": pi.pk, "dbgap_project_id": 1})
        new_object = models.dbGaPApplication.objects.latest("pk")
        self.assertRedirects(response, new_object.get_absolute_url())

    def test_success_message(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = self.api_client.sam_entry_point + "/api/groups/v1/TEST_PRIMED_DBGAP_ACCESS_1"
        self.anvil_response_mock.add(responses.POST, api_url, status=201, json={"message": "mock message"})
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            api_url + "/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(
            self.get_url(),
            {"principal_investigator": pi.pk, "dbgap_project_id": 1},
            follow=True,
        )
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(views.dbGaPApplicationCreate.success_message, str(messages[0]))

    def test_error_missing_pi(self):
        """Form shows an error when principal_investigator is missing."""
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"dbgap_project_id": 1})
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPApplication.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("principal_investigator", form.errors)
        self.assertEqual(len(form.errors["principal_investigator"]), 1)
        self.assertIn("required", form.errors["principal_investigator"][0])

    def test_invalid_pi(self):
        """Form shows an error when principal_investigator pk does not exist."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {"principal_investigator": self.user.pk + 1, "dbgap_project_id": 12345},
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPApplication.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("principal_investigator", form.errors)
        self.assertEqual(len(form.errors["principal_investigator"]), 1)
        self.assertIn("valid choice", form.errors["principal_investigator"][0])

    def test_error_missing_project_id(self):
        """Form shows an error when dbgap_phs is missing."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        response = self.client.post(self.get_url(), {"principal_investigator": pi.pk})
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPApplication.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_project_id", form.errors)
        self.assertEqual(len(form.errors["dbgap_project_id"]), 1)
        self.assertIn("required", form.errors["dbgap_project_id"][0])

    def test_error_duplicate_project_id(self):
        """Form shows an error when trying to create a duplicate dbgap_phs."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        other_pi = UserFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {
                "principal_investigator": other_pi.pk,
                "dbgap_project_id": dbgap_application.dbgap_project_id,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPApplication.objects.count(), 1)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_project_id", form.errors)
        self.assertEqual(len(form.errors["dbgap_project_id"]), 1)
        self.assertIn("already exists", form.errors["dbgap_project_id"][0])

    def test_post_blank_data(self):
        """Posting blank data does not create an object."""
        request = self.factory.post(self.get_url(), {})
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 2)
        self.assertIn("principal_investigator", form.errors.keys())
        self.assertEqual(len(form.errors["principal_investigator"]), 1)
        self.assertIn("required", form.errors["principal_investigator"][0])
        self.assertIn("dbgap_project_id", form.errors.keys())
        self.assertEqual(len(form.errors["dbgap_project_id"]), 1)
        self.assertIn("required", form.errors["dbgap_project_id"][0])
        self.assertEqual(models.dbGaPApplication.objects.count(), 0)

    def test_creates_anvil_access_group(self):
        """View creates a managed group upon when form is valid."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = self.api_client.sam_entry_point + "/api/groups/v1/TEST_PRIMED_DBGAP_ACCESS_12498"
        self.anvil_response_mock.add(responses.POST, api_url, status=201, json={"message": "mock message"})
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            api_url + "/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        response = self.client.post(self.get_url(), {"principal_investigator": pi.pk, "dbgap_project_id": 12498})
        self.assertEqual(response.status_code, 302)
        new_object = models.dbGaPApplication.objects.latest("pk")
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "TEST_PRIMED_DBGAP_ACCESS_12498")
        self.assertTrue(new_group.is_managed_by_app)
        # Also creates the CC admins group membership
        membership = GroupGroupMembership.objects.get(
            parent_group=new_group,
            child_group=self.cc_admin_group,
        )
        self.assertEqual(membership.role, GroupGroupMembership.ADMIN)

    @override_settings(ANVIL_DATA_ACCESS_GROUP_PREFIX="foo")
    def test_creates_anvil_access_group_different_setting_data_access_group_prefix(
        self,
    ):
        """View creates a managed group upon when form is valid."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = self.api_client.sam_entry_point + "/api/groups/v1/foo_DBGAP_ACCESS_12498"
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            api_url + "/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        self.anvil_response_mock.add(responses.POST, api_url, status=201, json={"message": "mock message"})
        response = self.client.post(self.get_url(), {"principal_investigator": pi.pk, "dbgap_project_id": 12498})
        self.assertEqual(response.status_code, 302)
        new_object = models.dbGaPApplication.objects.latest("pk")
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "foo_DBGAP_ACCESS_12498")
        self.assertTrue(new_group.is_managed_by_app)
        # Also creates the CC admins group membership
        membership = GroupGroupMembership.objects.get(
            parent_group=new_group,
            child_group=self.cc_admin_group,
        )
        self.assertEqual(membership.role, GroupGroupMembership.ADMIN)

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="foo")
    def test_creates_anvil_access_group_different_setting_cc_admin_group(self):
        """View creates a managed group upon when form is valid."""
        admin_group = ManagedGroupFactory.create(name="foo", email="foo@firecloud.org")
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = self.api_client.sam_entry_point + "/api/groups/v1/TEST_PRIMED_DBGAP_ACCESS_12498"
        self.anvil_response_mock.add(responses.POST, api_url, status=201, json={"message": "mock message"})
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            api_url + "/admin/foo@firecloud.org",
            status=204,
        )
        response = self.client.post(self.get_url(), {"principal_investigator": pi.pk, "dbgap_project_id": 12498})
        self.assertEqual(response.status_code, 302)
        new_object = models.dbGaPApplication.objects.latest("pk")
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_access_group, new_group)
        self.assertEqual(new_group.name, "TEST_PRIMED_DBGAP_ACCESS_12498")
        self.assertTrue(new_group.is_managed_by_app)
        # Also creates the CC admins group membership
        membership = GroupGroupMembership.objects.get(
            parent_group=new_group,
            child_group=admin_group,
        )
        self.assertEqual(membership.role, GroupGroupMembership.ADMIN)

    def test_manage_group_create_api_error(self):
        """Nothing is created when the form is valid but there is an API error when creating the group."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = self.api_client.sam_entry_point + "/api/groups/v1/TEST_PRIMED_DBGAP_ACCESS_1"
        self.anvil_response_mock.add(responses.POST, api_url, status=500, json={"message": "other error"})
        response = self.client.post(self.get_url(), {"principal_investigator": pi.pk, "dbgap_project_id": 1})
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        # ...but there was some error from the API.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual("AnVIL API Error: other error", str(messages[0]))
        # No objects were created.
        self.assertEqual(models.dbGaPApplication.objects.count(), 0)
        self.assertEqual(ManagedGroup.objects.count(), 1)  # Just the admin group.

    def test_managed_group_already_exists_in_app(self):
        """No objects are created if the managed group already exists in the app."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # Create a group with the same name.
        ManagedGroupFactory.create(name="TEST_PRIMED_DBGAP_ACCESS_1")
        response = self.client.post(self.get_url(), {"principal_investigator": pi.pk, "dbgap_project_id": 1})
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        # ...but there was an error with the group name.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(views.dbGaPApplicationCreate.ERROR_CREATING_GROUP, str(messages[0]))
        # No dbGaPApplication was created.
        self.assertEqual(models.dbGaPApplication.objects.count(), 0)

    def test_admin_group_membership_api_error(self):
        """Nothing is created when the form is valid but there is an API error when creating admin group membership."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_access_group.
        api_url = self.api_client.sam_entry_point + "/api/groups/v1/TEST_PRIMED_DBGAP_ACCESS_1"
        self.anvil_response_mock.add(responses.POST, api_url, status=201, json={"message": "other error"})
        # CC admins group membership.
        self.anvil_response_mock.add(
            responses.PUT,
            api_url + "/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=404,
            json={"message": "other error"},
        )
        response = self.client.post(self.get_url(), {"principal_investigator": pi.pk, "dbgap_project_id": 1})
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        # ...but there was some error from the API.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual("AnVIL API Error: other error", str(messages[0]))
        # No objects were created.
        self.assertEqual(models.dbGaPApplication.objects.count(), 0)
        self.assertEqual(ManagedGroup.objects.count(), 1)  # Just the admin group.


class dbGaPDataAccessSnapshotCreateTest(dbGaPResponseTestMixin, TestCase):
    """Tests for the dbGaPDataAccessRequestCreateFromJson view."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        self.model_factory = factories.StudyFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME)
        )
        self.dbgap_application = factories.dbGaPApplicationFactory.create()
        self.pi_name = fake.name()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "dbgap:dbgap_applications:dbgap_data_access_snapshots:new",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPDataAccessSnapshotCreate.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(self.dbgap_application.dbgap_project_id))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(self.dbgap_application.dbgap_project_id),
        )

    def test_status_code_with_user_permission_edit(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url(self.dbgap_application.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.dbgap_application.dbgap_project_id)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url(self.dbgap_application.dbgap_project_id))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, dbgap_project_id=self.dbgap_application.dbgap_project_id)

    def test_access_without_user_permission_view(self):
        """Raises permission denied if user has no permissions."""
        user_view_perm = User.objects.create_user(username="test-none", password="test-none")
        user_view_perm.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        request = self.factory.get(self.get_url(self.dbgap_application.dbgap_project_id))
        request.user = user_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, dbgap_project_id=self.dbgap_application.dbgap_project_id)

    def test_has_form_in_context(self):
        """Response includes a form."""
        request = self.factory.get(self.get_url(self.dbgap_application.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.dbgap_application.dbgap_project_id)
        self.assertTrue("form" in response.context_data)

    def test_form_class(self):
        """Form is the expected class."""
        request = self.factory.get(self.get_url(self.dbgap_application.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.dbgap_application.dbgap_project_id)
        self.assertIsInstance(response.context_data["form"], forms.dbGaPDataAccessSnapshotForm)

    def test_can_create_object(self):
        """Can create a dbGaPSnapshot and related dbGaPDataAccessRequests for this dbGaPApplication."""
        phs = "phs{phs:06d}".format(phs=fake.random_int())
        study_json = factories.dbGaPJSONStudyFactory(study_accession=phs)
        project_json = factories.dbGaPJSONProjectFactory(dbgap_application=self.dbgap_application, studies=[study_json])
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=" + phs + ".v1.p1"},
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps([project_json]),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # A snapshot object was created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 1)
        new_snapshot = models.dbGaPDataAccessSnapshot.objects.latest("pk")
        self.assertEqual(new_snapshot.dbgap_application, self.dbgap_application)
        self.assertEqual(new_snapshot.dbgap_dar_data, project_json)
        self.assertTrue(new_snapshot.is_most_recent)

    def test_can_create_object_and_related_dars(self):
        """Can create a dbGaPSnapshot and related dbGaPDataAccessRequests for this dbGaPApplication."""
        dar_json = factories.dbGaPJSONRequestFactory(
            DAR=1234,
            consent_code=1,
            consent_abbrev="foo",
            DAC_abbrev="DAC",
            current_version=22,
            current_DAR_status="approved",
            was_approved="yes",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession="phs000421", requests=[dar_json])
        project_json = factories.dbGaPJSONProjectFactory(dbgap_application=self.dbgap_application, studies=[study_json])
        # Add responses with the study version and participant_set.
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": "phs000421"})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"},
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps([project_json]),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 1)
        # Make sure all the correct objects were created.
        # dbGaPDataAccessSnapshot
        new_snapshot = models.dbGaPDataAccessSnapshot.objects.latest("pk")
        self.assertEqual(new_snapshot.dbgap_application, self.dbgap_application)
        self.assertEqual(new_snapshot.dbgap_dar_data, project_json)
        self.assertTrue(new_snapshot.is_most_recent)
        # dbGaPDataAccessRequest
        new_object = models.dbGaPDataAccessRequest.objects.get(dbgap_dar_id=1234)
        self.assertEqual(new_object.dbgap_data_access_snapshot, new_snapshot)
        self.assertEqual(new_object.dbgap_phs, 421)
        self.assertEqual(new_object.original_version, 32)
        self.assertEqual(new_object.original_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "foo")
        self.assertEqual(new_object.dbgap_dac, "DAC")

    def test_redirect_url(self):
        """Redirects to successful url."""
        # Add responses with the study version and participant_set.
        phs = "phs{phs:06d}".format(phs=fake.random_int())
        study_json = factories.dbGaPJSONStudyFactory(study_accession=phs)
        project_json = factories.dbGaPJSONProjectFactory(
            dbgap_application=self.dbgap_application,
            studies=[study_json],
        )
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id={}.v32.p18".format(phs)},
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps([project_json]),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertRedirects(response, self.dbgap_application.get_absolute_url())

    def test_success_message(self):
        """Redirects to successful url."""
        phs = "phs{phs:06d}".format(phs=fake.random_int())
        study_json = factories.dbGaPJSONStudyFactory(study_accession=phs)
        project_json = factories.dbGaPJSONProjectFactory(
            dbgap_application=self.dbgap_application,
            studies=[study_json],
        )
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id={}.v32.p18".format(phs)},
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps([project_json]),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
            follow=True,
        )
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(views.dbGaPDataAccessSnapshotCreate.success_message, str(messages[0]))

    def test_error_missing_json(self):
        """Form shows an error when dbgap_dar_data is missing."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": "",
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("required", form.errors["dbgap_dar_data"][0])

    def test_get_dbgap_application_pk_does_not_exist(self):
        """Raises a 404 error with an invalid object dbgap_application_pk."""
        request = self.factory.get(self.get_url(self.dbgap_application.pk + 999))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, dbgap_project_id=self.dbgap_application.pk + 999)

    def test_post_dbgap_application_pk_does_not_exist(self):
        """Raises a 404 error with an invalid object dbgap_application_pk."""
        request = self.factory.post(self.get_url(self.dbgap_application.pk + 999), {})
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, dbgap_project_id=self.dbgap_application.pk + 999)

    def test_has_form_when_one_snapshot_exists(self):
        phs_int = fake.random_int()
        phs = "phs{phs_int:06d}".format(phs_int=phs_int)
        request_json = factories.dbGaPJSONRequestFactory(
            DAR=1234,
            consent_code=1,
            consent_abbrev="GRU",
            current_DAR_status="approved",
            DAC_abbrev="FOOBAR",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession=phs, requests=[request_json])
        project_json = factories.dbGaPJSONProjectFactory(
            dbgap_application=self.dbgap_application,
            studies=[study_json],
        )
        existing_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=self.dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
        )
        # Create DARs for it.
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=existing_snapshot,
            dbgap_dar_id=1234,
            dbgap_phs=phs_int,
            dbgap_consent_code=1,
            dbgap_consent_abbreviation="GRU",
            dbgap_current_status="approved",
            dbgap_dac="FOOBAR",
            original_version=3,
            original_participant_set=2,
        )
        # Now try to load the page again.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.dbgap_application.dbgap_project_id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context_data)

    def test_updates_existing_snapshot_is_most_recent(self):
        """Updates the is_most_recent for older snapshots."""
        phs_int = fake.random_int()
        phs = "phs{phs_int:06d}".format(phs_int=phs_int)
        request_json = factories.dbGaPJSONRequestFactory(
            DAR=1234,
            consent_code=1,
            consent_abbrev="GRU",
            current_DAR_status="approved",
            DAC_abbrev="FOOBAR",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession=phs, requests=[request_json])
        project_json = factories.dbGaPJSONProjectFactory(
            dbgap_application=self.dbgap_application,
            studies=[study_json],
        )
        existing_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=self.dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=True,
        )
        # Create DARs for it.
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=existing_snapshot,
            dbgap_dar_id=1234,
            dbgap_phs=phs_int,
            dbgap_consent_code=1,
            dbgap_consent_abbreviation="GRU",
            dbgap_current_status="approved",
            dbgap_dac="FOOBAR",
            original_version=3,
            original_participant_set=2,
        )
        # Now add a new snapshot.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps([project_json]),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 2)
        new_snapshot = models.dbGaPDataAccessSnapshot.objects.latest("pk")
        self.assertEqual(new_snapshot.dbgap_application, self.dbgap_application)
        self.assertTrue(new_snapshot.is_most_recent)
        # Updates the old snapshot.
        existing_snapshot.refresh_from_db()
        self.assertFalse(existing_snapshot.is_most_recent)

    def test_can_add_a_second_snapshot_with_dars(self):
        """Can add a second snapshot and new DARs."""
        phs_int = fake.random_int()
        phs = "phs{phs_int:06d}".format(phs_int=phs_int)
        request_json = factories.dbGaPJSONRequestFactory(
            DAR=1234,
            consent_code=1,
            consent_abbrev="GRU",
            current_DAR_status="approved",
            DAC_abbrev="FOOBAR",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession=phs, requests=[request_json])
        project_json = factories.dbGaPJSONProjectFactory(
            dbgap_application=self.dbgap_application,
            studies=[study_json],
        )
        existing_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=self.dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=True,
        )
        # Create DARs for it.
        original_dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=existing_snapshot,
            dbgap_dar_id=1234,
            dbgap_phs=phs_int,
            dbgap_consent_code=1,
            dbgap_consent_abbreviation="GRU",
            dbgap_current_status="approved",
            dbgap_dac="FOOBAR",
        )
        # Now add a new snapshot.
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps([project_json]),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 2)
        new_snapshot = models.dbGaPDataAccessSnapshot.objects.latest("pk")
        self.assertEqual(new_snapshot.dbgap_application, self.dbgap_application)
        self.assertEqual(new_snapshot.dbgap_dar_data, project_json)
        self.assertEqual(new_snapshot.dbgapdataaccessrequest_set.count(), 1)
        # DARs are updated.
        new_dar = models.dbGaPDataAccessRequest.objects.latest("pk")
        self.assertEqual(new_dar.dbgap_data_access_snapshot, new_snapshot)
        self.assertEqual(new_dar.dbgap_dar_id, 1234)
        self.assertEqual(new_dar.dbgap_phs, phs_int)
        self.assertEqual(new_dar.dbgap_consent_code, 1)
        self.assertEqual(new_dar.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_dar.dbgap_current_status, "approved")
        # These should be obtained from the original dar.
        self.assertEqual(new_dar.original_version, original_dar.original_version)
        self.assertEqual(new_dar.original_participant_set, original_dar.original_participant_set)

    def test_post_invalid_json(self):
        """JSON is invalid."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps({"foo": "bar"}),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error", form.errors["dbgap_dar_data"][0])

    def test_json_project_id_does_not_match(self):
        """Error message when project_id in JSON does not match project_id in dbGaPApplication."""
        project_json = factories.dbGaPJSONProjectFactory(Project_id=self.dbgap_application.dbgap_project_id + 1)
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps([project_json]),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 0)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        # Form is not valid...
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("__all__", form.errors)
        self.assertEqual(len(form.errors["__all__"]), 1)
        self.assertIn("Project_id", form.errors["__all__"][0])

    def test_context_includes_dbgap_application(self):
        """Response context data includes the dbGaP application."""
        request = self.factory.get(self.get_url(self.dbgap_application.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.dbgap_application.dbgap_project_id)
        self.assertTrue("dbgap_application" in response.context_data)
        self.assertEqual(response.context_data["dbgap_application"], self.dbgap_application)

    def test_snapshot_not_created_if_http404(self):
        """The dbGaPDataAccessSnapshot is not created if DARs cannot be created due to a HTTP 404 response."""
        phs_int = fake.random_int()
        phs = "phs{phs_int:06d}".format(phs_int=phs_int)
        request_json = factories.dbGaPJSONRequestFactory(
            DAR=1234,
            consent_code=1,
            consent_abbrev="GRU",
            current_DAR_status="approved",
            DAC_abbrev="FOOBAR",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession=phs, requests=[request_json])
        project_json = factories.dbGaPJSONProjectFactory(
            dbgap_application=self.dbgap_application,
            studies=[study_json],
        )
        # Add responses with the study version and participant_set.
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=404,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps([project_json]),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No objects were created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 0)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)
        # response has an error message.
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(views.dbGaPDataAccessSnapshotCreate.ERROR_CREATING_DARS, str(messages[0]))

    def test_existing_snapshot_not_updated_http404(self):
        """The dbGaPDataAccessSnapshot is not created if there is an HTTP 404 error."""
        phs_int = fake.random_int()
        phs = "phs{phs_int:06d}".format(phs_int=phs_int)
        request_json = factories.dbGaPJSONRequestFactory(
            DAR=1234,
            consent_code=1,
            consent_abbrev="GRU",
            current_DAR_status="approved",
            DAC_abbrev="FOOBAR",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession=phs, requests=[request_json])
        project_json = factories.dbGaPJSONProjectFactory(
            dbgap_application=self.dbgap_application,
            studies=[study_json],
        )
        existing_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=self.dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=True,
        )
        # Add responses with the study version and participant_set.
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=404,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps([project_json]),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 1)
        existing_snapshot.refresh_from_db()
        self.assertTrue(existing_snapshot.is_most_recent)

    def test_snapshot_not_created_if_dar_error(self):
        """The dbGaPDataAccessSnapshot is not created if DARs cannot be created due to duplicated DAR id."""
        phs = "phs{phs_int:06d}".format(phs_int=fake.random_int())
        request_json_1 = factories.dbGaPJSONRequestFactory(
            DAR=1234,
            consent_code=1,
            consent_abbrev="GRU",
            current_DAR_status="approved",
            DAC_abbrev="FOOBAR",
        )
        request_json_2 = factories.dbGaPJSONRequestFactory(
            DAR=1234,
            consent_code=2,
            consent_abbrev="HMB",
            current_DAR_status="approved",
            DAC_abbrev="FOOBAR",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession=phs, requests=[request_json_1, request_json_2])
        project_json = factories.dbGaPJSONProjectFactory(
            dbgap_application=self.dbgap_application,
            studies=[study_json],
        )
        # Add responses with the study version and participant_set.
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"},
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps([project_json]),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No objects were created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 0)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    def test_existing_snapshot_is_most_recent_with_dar_errors(self):
        """An existing dbGaPDataAccessSnapshot.is_most_recent value is not updated if DARs cannot be created."""
        phs = "phs{phs_int:06d}".format(phs_int=fake.random_int())
        request_json_1 = factories.dbGaPJSONRequestFactory(
            DAR=1234,
            consent_code=1,
            consent_abbrev="GRU",
            current_DAR_status="approved",
            DAC_abbrev="FOOBAR",
        )
        request_json_2 = factories.dbGaPJSONRequestFactory(
            DAR=1234,
            consent_code=2,
            consent_abbrev="HMB",
            current_DAR_status="approved",
            DAC_abbrev="FOOBAR",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession=phs, requests=[request_json_1, request_json_2])
        project_json = factories.dbGaPJSONProjectFactory(
            dbgap_application=self.dbgap_application,
            studies=[study_json],
        )
        # Add responses with the study version and participant_set.
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"},
        )
        # Create an existing snapshot.
        existing_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=self.dbgap_application,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=True,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.dbgap_project_id),
            {
                "dbgap_dar_data": json.dumps([project_json]),
                # Note that the post data needs to include the dbGaP application in tests.
                "dbgap_application": self.dbgap_application.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        # No objects were created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 1)
        existing_snapshot.refresh_from_db()
        self.assertTrue(existing_snapshot.is_most_recent)


class dbGaPDataAccessSnapshotCreateMultipleTest(dbGaPResponseTestMixin, TestCase):
    """Tests for the dbGaPDataAccessRequestCreateFromJson view."""

    def setUp(self):
        """Set up test class."""
        # Make sure no actual calls are made, so activate responses for every test.
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME)
        )

    def tearDown(self):
        super().tearDown()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "dbgap:dbgap_applications:update_dars",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPDataAccessSnapshotCreateMultiple.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission_edit(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_access_without_user_permission_view(self):
        """Raises permission denied if user has no permissions."""
        user_view_perm = User.objects.create_user(username="test-none", password="test-none")
        user_view_perm.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        request = self.factory.get(self.get_url())
        request.user = user_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_has_form_in_context(self):
        """Response includes a form."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertTrue("form" in response.context_data)

    def test_form_class(self):
        """Form is the expected class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIsInstance(response.context_data["form"], forms.dbGaPDataAccessSnapshotMultipleForm)

    def test_context_dbgap_dar_json_url(self):
        """Response context includes dbgap_dar_json_url."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertTrue("dbgap_dar_json_url" in response.context_data)

    def test_updates_one_application(self):
        dbgap_application = factories.dbGaPApplicationFactory.create()
        project_json = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application)
        phs = project_json["studies"][0]["study_accession"]
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=" + phs + ".v1.p1"},
        )
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"dbgap_dar_data": json.dumps([project_json])})
        self.assertEqual(response.status_code, 302)
        dbgap_application.refresh_from_db()
        self.assertEqual(dbgap_application.dbgapdataaccesssnapshot_set.count(), 1)
        new_snapshot = dbgap_application.dbgapdataaccesssnapshot_set.latest("pk")
        self.assertEqual(new_snapshot.dbgapdataaccessrequest_set.count(), 1)

    def test_updates_two_applications(self):
        # First application and associated JSON.
        dbgap_application_1 = factories.dbGaPApplicationFactory.create()
        project_json_1 = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application_1)
        phs_1 = project_json_1["studies"][0]["study_accession"]
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs_1})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=" + phs_1 + ".v1.p1"},
        )
        # Second application and associated JSON.
        dbgap_application_2 = factories.dbGaPApplicationFactory.create()
        project_json_2 = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application_2)
        phs_2 = project_json_2["studies"][0]["study_accession"]
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs_2})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=" + phs_2 + ".v2.p2"},
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {"dbgap_dar_data": json.dumps([project_json_1, project_json_2])},
        )
        self.assertEqual(response.status_code, 302)
        # Check first application.
        dbgap_application_1.refresh_from_db()
        self.assertEqual(dbgap_application_1.dbgapdataaccesssnapshot_set.count(), 1)
        new_snapshot_1 = dbgap_application_1.dbgapdataaccesssnapshot_set.latest("pk")
        self.assertEqual(new_snapshot_1.dbgapdataaccessrequest_set.count(), 1)
        # Check second
        dbgap_application_2.refresh_from_db()
        self.assertEqual(dbgap_application_2.dbgapdataaccesssnapshot_set.count(), 1)
        new_snapshot_2 = dbgap_application_2.dbgapdataaccesssnapshot_set.latest("pk")
        self.assertEqual(new_snapshot_2.dbgapdataaccessrequest_set.count(), 1)

    def test_redirect_url(self):
        """Redirects to successful url."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        project_json = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application)
        phs = project_json["studies"][0]["study_accession"]
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=" + phs + ".v1.p1"},
        )
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"dbgap_dar_data": json.dumps([project_json])})
        self.assertRedirects(response, reverse("dbgap:dbgap_applications:list"))

    def test_success_message(self):
        """Redirects to successful url."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        project_json = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application)
        phs = project_json["studies"][0]["study_accession"]
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=" + phs + ".v1.p1"},
        )
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"dbgap_dar_data": json.dumps([project_json])}, follow=True)
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.dbGaPDataAccessSnapshotCreateMultiple.success_message,
            str(messages[0]),
        )

    def test_error_blank_dbgap_dar_data(self):
        """Form shows an error when study is missing."""
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"dbgap_dar_data": ""})
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("required", form.errors["dbgap_dar_data"][0])

    def test_dbgap_application_does_not_exist(self):
        """Shows an error when the dbGaP application does not exist."""
        project_json = factories.dbGaPJSONProjectFactory()
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"dbgap_dar_data": json.dumps([project_json])})
        self.assertEqual(response.status_code, 200)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("not exist", form.errors["dbgap_dar_data"][0])
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 0)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    def test_second_dbgap_application_does_not_exist(self):
        """Shows an error when one dbGaP application does not exist."""
        dbgap_application_1 = factories.dbGaPApplicationFactory.create()
        project_json_1 = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application_1)
        project_json_2 = factories.dbGaPJSONProjectFactory()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {"dbgap_dar_data": json.dumps([project_json_1, project_json_2])},
        )
        self.assertEqual(response.status_code, 200)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("not exist", form.errors["dbgap_dar_data"][0])
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 0)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    def test_updates_existing_snapshot_is_most_recent(self):
        """Updates the is_most_recent for older snapshots."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        project_json = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application)
        phs = project_json["studies"][0]["study_accession"]
        existing_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=True,
        )
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=" + phs + ".v1.p1"},
        )
        # Now add a new snapshot.
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"dbgap_dar_data": json.dumps([project_json])})
        self.client.force_login(self.user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 2)
        new_snapshot = models.dbGaPDataAccessSnapshot.objects.latest("pk")
        self.assertEqual(new_snapshot.dbgap_application, dbgap_application)
        self.assertEqual(new_snapshot.dbgap_dar_data, project_json)
        self.assertTrue(new_snapshot.is_most_recent)
        # Updates the old snapshot.
        existing_snapshot.refresh_from_db()
        self.assertFalse(existing_snapshot.is_most_recent)

    def test_can_add_a_second_snapshot_with_dars(self):
        """Can add a second snapshot and new DARs."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        project_json = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application)
        phs = project_json["studies"][0]["study_accession"]
        factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=True,
        )
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=" + phs + ".v1.p1"},
        )
        # Now add a new snapshot.
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"dbgap_dar_data": json.dumps([project_json])})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 2)
        new_snapshot = models.dbGaPDataAccessSnapshot.objects.latest("pk")
        self.assertEqual(new_snapshot.dbgap_application, dbgap_application)
        self.assertEqual(new_snapshot.dbgap_dar_data, project_json)
        self.assertEqual(new_snapshot.dbgapdataaccessrequest_set.count(), 1)

    def test_post_invalid_json(self):
        """JSON is invalid."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {"dbgap_dar_data": json.dumps({"foo": "bar"})},
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error", form.errors["dbgap_dar_data"][0])

    def test_snapshot_not_created_if_http404(self):
        """The dbGaPDataAccessSnapshot is not created if DARs cannot be created due to a HTTP 404 response."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        project_json = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application)
        phs = project_json["studies"][0]["study_accession"]
        # Add responses with the study version and participant_set.
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=404,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {
                "dbgap_dar_data": json.dumps([project_json]),
            },
        )
        self.assertEqual(response.status_code, 200)
        # No form errors but...
        self.assertIn("form", response.context_data)
        self.assertTrue(response.context_data["form"].is_valid())
        # There is an error message.
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.dbGaPDataAccessSnapshotCreateMultiple.ERROR_CREATING_DARS,
            str(messages[0]),
        )
        # No objects were created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 0)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    def test_existing_snapshot_not_updated_http404(self):
        """The dbGaPDataAccessSnapshot is not created if there is an HTTP 404 error."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        project_json = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application)
        phs = project_json["studies"][0]["study_accession"]
        existing_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=True,
        )
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=404,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {
                "dbgap_dar_data": json.dumps([project_json]),
            },
        )
        self.assertEqual(response.status_code, 200)
        # No form errors but...
        self.assertIn("form", response.context_data)
        self.assertTrue(response.context_data["form"].is_valid())
        # There is an error message.
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.dbGaPDataAccessSnapshotCreateMultiple.ERROR_CREATING_DARS,
            str(messages[0]),
        )
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 1)
        existing_snapshot.refresh_from_db()
        self.assertTrue(existing_snapshot.is_most_recent)

    def test_snapshot_not_created_if_dar_validation_error(self):
        """The dbGaPDataAccessSnapshot is not created if DARs cannot be created."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        request_json_1 = factories.dbGaPJSONRequestFactory(DAR=12345)
        request_json_2 = factories.dbGaPJSONRequestFactory(DAR=12345)
        study_json = factories.dbGaPJSONStudyFactory(requests=[request_json_1, request_json_2])
        project_json = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application, studies=[study_json])
        phs = project_json["studies"][0]["study_accession"]
        # Add responses with the study version and participant_set.
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=" + phs + ".v32.p18"},
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {
                "dbgap_dar_data": json.dumps([project_json]),
            },
        )
        self.assertEqual(response.status_code, 200)
        # No form errors but...
        self.assertIn("form", response.context_data)
        self.assertTrue(response.context_data["form"].is_valid())
        # There is an error message.
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.dbGaPDataAccessSnapshotCreateMultiple.ERROR_CREATING_DARS,
            str(messages[0]),
        )
        # No objects were created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 0)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    def test_existing_snapshot_is_most_recent_with_dar_validation_error(self):
        """An existing dbGaPDataAccessSnapshot.is_most_recent value is not updated if DARs cannot be created."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        request_json_1 = factories.dbGaPJSONRequestFactory(DAR=12345)
        request_json_2 = factories.dbGaPJSONRequestFactory(DAR=12345)
        study_json = factories.dbGaPJSONStudyFactory(requests=[request_json_1, request_json_2])
        project_json = factories.dbGaPJSONProjectFactory(dbgap_application=dbgap_application, studies=[study_json])
        phs = project_json["studies"][0]["study_accession"]

        existing_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=True,
        )
        # Add responses with the study version and participant_set.
        self.dbgap_response_mock.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": phs})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=" + phs + ".v32.p18"},
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {
                "dbgap_dar_data": json.dumps([project_json]),
            },
        )
        self.assertEqual(response.status_code, 200)
        # No form errors but...
        self.assertIn("form", response.context_data)
        self.assertTrue(response.context_data["form"].is_valid())
        # There is an error message.
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.dbGaPDataAccessSnapshotCreateMultiple.ERROR_CREATING_DARS,
            str(messages[0]),
        )
        # No objects were created.
        self.assertEqual(models.dbGaPDataAccessSnapshot.objects.count(), 1)
        existing_snapshot.refresh_from_db()
        self.assertTrue(existing_snapshot.is_most_recent)


class dbGaPDataAccessSnapshotDetailTest(TestCase):
    """Tests for the dbGaPDataAccessRequestAudit view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.application = factories.dbGaPApplicationFactory.create()
        self.snapshot = factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=self.application)

    def tearDown(self):
        super().tearDown()
        responses.stop()
        responses.reset()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "dbgap:dbgap_applications:dbgap_data_access_snapshots:detail",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPDataAccessSnapshotDetail.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL)
            + "?next="
            + self.get_url(self.application.dbgap_project_id, self.snapshot.pk),
        )

    def test_status_code_with_user_permission_view(self):
        """Returns successful response code if the user has view permission."""
        request = self.factory.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        request.user = self.user
        response = self.get_view()(
            request,
            dbgap_project_id=self.application.dbgap_project_id,
            dbgap_data_access_snapshot_pk=self.snapshot.pk,
        )
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(
                request,
                dbgap_project_id=self.application.dbgap_project_id,
                dbgap_data_access_snapshot_pk=self.snapshot.pk,
            )

    def test_invalid_dbgap_application_pk(self):
        """Raises a 404 error with an invalid object dbgap_application_pk."""
        request = self.factory.get(self.get_url(self.application.dbgap_project_id + 1, self.snapshot.pk))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(
                request,
                dbgap_project_id=self.application.dbgap_project_id + 1,
                dbgap_data_access_snapshot_pk=self.snapshot.pk,
            )

    def test_invalid_dbgap_data_access_snapshot_pk(self):
        """Raises a 404 error with an invalid object dbgap_data_access_snapshot_pk."""
        request = self.factory.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(
                request,
                dbgap_project_id=self.application.dbgap_project_id,
                dbgap_data_access_snapshot_pk=self.snapshot.pk + 1,
            )

    def test_mismatch_application_snapshot(self):
        """Raises a 404 error when dbgap application and snapshot pk don't match."""
        other_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        request = self.factory.get(self.get_url(self.application.dbgap_project_id, other_snapshot.pk))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(
                request,
                dbgap_project_id=self.application.dbgap_project_id,
                dbgap_data_access_snapshot_pk=other_snapshot.pk,
            )

    def test_context_dar_table(self):
        """The data_access_request_table exists in the context."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        self.assertIn("data_access_request_table", response.context_data)
        self.assertIsInstance(
            response.context_data["data_access_request_table"],
            tables.dbGaPDataAccessRequestBySnapshotTable,
        )

    def test_context_dar_table_none(self):
        """The data_access_request_table works with one DAR."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        self.assertIn("data_access_request_table", response.context_data)
        self.assertEqual(len(response.context_data["data_access_request_table"].rows), 0)

    def test_context_dar_table_one(self):
        """The data_access_request_table works with one DAR."""
        dar = factories.dbGaPDataAccessRequestFactory.create(dbgap_data_access_snapshot=self.snapshot)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        self.assertIn("data_access_request_table", response.context_data)
        self.assertEqual(len(response.context_data["data_access_request_table"].rows), 1)
        self.assertIn(dar, response.context_data["data_access_request_table"].data)

    def test_context_dar_table_two(self):
        """The data_access_request_table works with one DAR."""
        dars = factories.dbGaPDataAccessRequestFactory.create_batch(2, dbgap_data_access_snapshot=self.snapshot)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        self.assertIn("data_access_request_table", response.context_data)
        self.assertEqual(len(response.context_data["data_access_request_table"].rows), 2)
        self.assertIn(dars[0], response.context_data["data_access_request_table"].data)
        self.assertIn(dars[1], response.context_data["data_access_request_table"].data)

    def test_context_dar_table_only_shows_dars_for_this_snapshot(self):
        """The data_access_request_table only shows DARs associated with this snapshot."""
        dar = factories.dbGaPDataAccessRequestFactory.create(dbgap_data_access_snapshot=self.snapshot)
        other_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=self.application)
        other_dar = factories.dbGaPDataAccessRequestFactory.create(dbgap_data_access_snapshot=other_snapshot)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        self.assertIn("data_access_request_table", response.context_data)
        self.assertEqual(len(response.context_data["data_access_request_table"].rows), 1)
        self.assertIn(dar, response.context_data["data_access_request_table"].data)
        self.assertNotIn(other_dar, response.context_data["data_access_request_table"].data)

    def test_context_summary_table(self):
        """The data_access_request_table exists in the context."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        self.assertIn("summary_table", response.context_data)
        self.assertIsInstance(
            response.context_data["summary_table"],
            tables.dbGaPDataAccessRequestSummaryTable,
        )

    def test_context_summary_table_none(self):
        """The data_access_request_table works with no DARs."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        self.assertIn("summary_table", response.context_data)
        self.assertEqual(len(response.context_data["summary_table"].rows), 0)

    def test_context_summary_table_contents(self):
        """The data_access_request_table contents are correct."""
        # 1 FOO approved
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=self.snapshot,
            dbgap_dac="FOO",
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        # 2 FOO New
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=self.snapshot,
            dbgap_dac="FOO",
            dbgap_current_status=models.dbGaPDataAccessRequest.NEW,
        )
        # 3 BAR Approved
        factories.dbGaPDataAccessRequestFactory.create_batch(
            3,
            dbgap_data_access_snapshot=self.snapshot,
            dbgap_dac="BAR",
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        # 4 BAR New
        factories.dbGaPDataAccessRequestFactory.create_batch(
            4,
            dbgap_data_access_snapshot=self.snapshot,
            dbgap_dac="BAR",
            dbgap_current_status=models.dbGaPDataAccessRequest.NEW,
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        self.assertIn("summary_table", response.context_data)
        table = response.context_data["summary_table"]

        # verify rows are all in table in ordered queryset order
        # alphabetical dac, status
        self.assertEqual(len(table.rows), 4)
        self.assertEqual(table.rows[0].get_cell_value("dbgap_dac"), "BAR")
        self.assertEqual(
            table.rows[0].get_cell_value("dbgap_current_status"),
            models.dbGaPDataAccessRequest.APPROVED,
        )
        self.assertEqual(table.rows[0].get_cell_value("total"), 3)
        self.assertEqual(table.rows[1].get_cell_value("dbgap_dac"), "BAR")
        self.assertEqual(
            table.rows[1].get_cell_value("dbgap_current_status"),
            models.dbGaPDataAccessRequest.NEW,
        )
        self.assertEqual(table.rows[1].get_cell_value("total"), 4)
        self.assertEqual(table.rows[2].get_cell_value("dbgap_dac"), "FOO")
        self.assertEqual(
            table.rows[2].get_cell_value("dbgap_current_status"),
            models.dbGaPDataAccessRequest.APPROVED,
        )
        self.assertEqual(table.rows[2].get_cell_value("total"), 1)
        self.assertEqual(table.rows[3].get_cell_value("dbgap_dac"), "FOO")
        self.assertEqual(
            table.rows[3].get_cell_value("dbgap_current_status"),
            models.dbGaPDataAccessRequest.NEW,
        )
        self.assertEqual(table.rows[3].get_cell_value("total"), 2)

    def test_context_summary_table_only_shows_dars_for_this_snapshot(self):
        """The data_access_request_table only shows DARs associated with this snapshot."""
        other_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=self.application)
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=other_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
            dbgap_dac="FOO",
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        self.assertIn("summary_table", response.context_data)
        table = response.context_data["summary_table"]
        self.assertEqual(len(table.rows), 0)

    def test_no_alert_for_most_recent_snapshot(self):
        """No alert is shown when this is the most recent snapshot for an application."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id, self.snapshot.pk))
        self.assertNotContains(response, "not the most recent snapshot", status_code=200)

    def test_alert_when_not_most_recent_snapshot(self):
        """An alert is shown when this is not the most recent snapshot for an application."""
        old_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=self.application,
            created=timezone.now() - timedelta(weeks=5),
            is_most_recent=False,
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id, old_snapshot.pk))
        self.assertContains(response, "not the most recent snapshot", status_code=200)


class dbGaPDataAccessRequestListTest(TestCase):
    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:dars:current", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPDataAccessRequestList.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_table_class(self):
        """The table is the correct class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertIsInstance(response.context_data["table"], tables.dbGaPDataAccessRequestTable)

    def test_one_dar(self):
        """Table displays one dar."""
        dar = factories.dbGaPDataAccessRequestFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn(dar, response.context_data["table"].data)

    def test_two_dars(self):
        """Table displays two dars."""
        dar_1 = factories.dbGaPDataAccessRequestFactory.create()
        dar_2 = factories.dbGaPDataAccessRequestFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn(dar_1, response.context_data["table"].data)
        self.assertIn(dar_2, response.context_data["table"].data)

    def test_only_current_dars_shown(self):
        dar = factories.dbGaPDataAccessRequestFactory.create(dbgap_data_access_snapshot__is_most_recent=False)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertNotIn(dar, response.context_data["table"].data)

    def test_context_export_button(self):
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertContains(response, self.get_url() + "?_export=tsv")

    def test_export(self):
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(), {"_export": "tsv"})
        self.assertIn("Content-Type", response)
        self.assertEqual(response["Content-Type"], "text/tsv; charset=utf-8")
        self.assertIn("Content-Disposition", response)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="dars_table.tsv"')


class dbGaPDataAccessRequestHistoryTest(TestCase):
    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:dars:history", args=args)

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPDataAccessRequestHistory.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        instance = factories.dbGaPDataAccessRequestFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.dbgap_dar_id))
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url(1))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, 1)

    def test_dbgap_dar_id_does_not_exist(self):
        """Raises permission denied if user has no permissions."""
        request = self.factory.get(self.get_url(1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, 1)

    def test_table_class(self):
        """The table is the correct class."""
        instance = factories.dbGaPDataAccessRequestFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(instance.dbgap_dar_id))
        self.assertIn("table", response.context_data)
        self.assertIsInstance(response.context_data["table"], tables.dbGaPDataAccessRequestHistoryTable)

    def test_one_dars(self):
        """Table displays two dars."""
        dar = factories.dbGaPDataAccessRequestFactory.create(dbgap_dar_id=1)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(1))
        self.assertEqual(len(response.context_data["table"].rows), 1)
        self.assertIn(dar, response.context_data["table"].data)

    def test_two_dars(self):
        """Table displays two dars."""
        dar_1 = factories.dbGaPDataAccessRequestFactory.create(dbgap_dar_id=1)
        dar_2 = factories.dbGaPDataAccessRequestFactory.create(dbgap_dar_id=1)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(1))
        self.assertEqual(len(response.context_data["table"].rows), 2)
        self.assertIn(dar_1, response.context_data["table"].data)
        self.assertIn(dar_2, response.context_data["table"].data)

    def test_matching_dbgap_dar_id(self):
        """Only DARs with the same dbgap_dar_id are in the table."""
        dar_1 = factories.dbGaPDataAccessRequestFactory.create(dbgap_dar_id=1)
        dar_2 = factories.dbGaPDataAccessRequestFactory.create(dbgap_dar_id=2)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(1))
        self.assertEqual(len(response.context_data["table"].rows), 1)
        self.assertIn(dar_1, response.context_data["table"].data)
        self.assertNotIn(dar_2, response.context_data["table"].data)

    def test_table_ordering(self):
        """DARs from the most recent snapshot appear first."""
        old_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            created=timezone.now() - timedelta(weeks=5),
            is_most_recent=False,
        )
        dar_1 = factories.dbGaPDataAccessRequestFactory.create(dbgap_dar_id=1, dbgap_data_access_snapshot=old_snapshot)
        new_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            created=timezone.now() - timedelta(weeks=1),
            is_most_recent=True,
        )
        dar_2 = factories.dbGaPDataAccessRequestFactory.create(dbgap_dar_id=1, dbgap_data_access_snapshot=new_snapshot)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(1))
        self.assertEqual(len(response.context_data["table"].rows), 2)
        self.assertEqual(dar_2, response.context_data["table"].rows[0].record)
        self.assertEqual(dar_1, response.context_data["table"].rows[1].record)


class dbGaPApplicationAuditTest(TestCase):
    """Tests for the dbGaPApplicationAudit view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.application = factories.dbGaPApplicationFactory.create()
        self.snapshot = factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=self.application)

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "dbgap:audit:applications",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPApplicationAudit.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(self.application.dbgap_project_id))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(self.application.dbgap_project_id),
        )

    def test_status_code_with_user_permission_view(self):
        """Returns successful response code if the user has view permission."""
        request = self.factory.get(self.get_url(self.application.dbgap_project_id))
        request.user = self.user
        response = self.get_view()(request, dbgap_project_id=self.application.dbgap_project_id)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url(self.application.dbgap_project_id))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, dbgap_project_id=self.application.dbgap_project_id)

    def test_invalid_dbgap_application_pk(self):
        """Raises a 404 error with an invalid object dbgap_application_pk."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id + 1))
        self.assertEqual(response.status_code, 404)

    def test_context_data_access_audit(self):
        """The data_access_audit exists in the context."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id))
        self.assertIn("data_access_audit", response.context_data)
        data_access_audit = response.context_data["data_access_audit"]
        self.assertIsInstance(
            data_access_audit,
            audit.dbGaPAccessAudit,
        )
        self.assertTrue(data_access_audit.completed)
        self.assertEqual(data_access_audit.dbgap_application_queryset.count(), 1)
        self.assertIn(self.application, data_access_audit.dbgap_application_queryset)

    def test_context_data_access_audit_does_not_include_other_applications(self):
        """The data_access_audit does not include other applications."""
        other_application = factories.dbGaPApplicationFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id))
        data_access_audit = response.context_data["data_access_audit"]
        self.assertEqual(data_access_audit.dbgap_application_queryset.count(), 1)
        self.assertNotIn(other_application, data_access_audit.dbgap_application_queryset)

    def test_context_verified_table_access(self):
        """verified_table shows a record when audit has verified access."""
        # Add a verified workspace.
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_study_accession__dbgap_phs=1)
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_data_access_snapshot=self.snapshot, dbgap_workspace=workspace
        )
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.snapshot.dbgap_application.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id))
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.APPROVED_DAR,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_verified_table_no_access(self):
        """verified_table shows a record when audit has verified no access."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id))
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertIsNone(table.rows[0].get_cell_value("data_access_request"))
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.NO_DAR,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_needs_action_table_grant(self):
        """needs_action_table shows a record when audit finds that access needs to be granted."""
        workspace = factories.dbGaPWorkspaceFactory.create(created=timezone.now() - timedelta(weeks=4))
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_data_access_snapshot=self.snapshot, dbgap_workspace=workspace
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id))
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.NEW_APPROVED_DAR,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_needs_action_table_remove(self):
        """needs_action_table shows a record when audit finds that access needs to be removed."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_data_access_snapshot=self.snapshot,
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        # Create an old dar that was approved
        old_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=self.application,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=False,
        )
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=dar.dbgap_dar_id,
            dbgap_data_access_snapshot=old_snapshot,
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.snapshot.dbgap_application.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id))
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.PREVIOUS_APPROVAL,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_error_table_has_access(self):
        """error shows a record when audit finds that access needs to be removed."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        # Create a rejected DAR.
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_data_access_snapshot=self.snapshot,
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        # Create the membership.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.snapshot.dbgap_application.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id))
        self.assertIn("errors_table", response.context_data)
        table = response.context_data["errors_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.ERROR_HAS_ACCESS,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_latest_snapshot(self):
        # Create an old dar that was approved
        factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=self.application,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=False,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.application.dbgap_project_id))
        self.assertIn("latest_snapshot", response.context)
        self.assertEqual(response.context["latest_snapshot"], self.snapshot)

    def test_no_snapshots(self):
        """Audit is not run and message shown when there are no snapshots for this application."""
        factories.dbGaPWorkspaceFactory.create()
        application = factories.dbGaPApplicationFactory.create()
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(application.dbgap_project_id))
        self.assertIn("latest_snapshot", response.context)
        self.assertIsNone(response.context["latest_snapshot"])
        self.assertNotIn("verified_table", response.context)
        self.assertNotIn("errors_table", response.context)
        self.assertNotIn("needs_action_table", response.context)
        self.assertNotIn("data_access_audit", response.context)
        self.assertIn("No data access snapshots", str(response.content))


class dbGaPWorkspaceAuditTest(TestCase):
    """Tests for the dbGaPWorkspaceAudit view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.dbgap_workspace = factories.dbGaPWorkspaceFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "dbgap:audit:workspaces",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPWorkspaceAudit.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url("foo", "bar"))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url("foo", "bar"),
        )

    def test_status_code_with_user_permission_view(self):
        """Returns successful response code if the user has view permission."""
        request = self.factory.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        request.user = self.user
        response = self.get_view()(
            request,
            billing_project_slug=self.dbgap_workspace.workspace.billing_project.name,
            workspace_slug=self.dbgap_workspace.workspace.name,
        )
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(
                request,
                billing_project_slug=self.dbgap_workspace.workspace.billing_project.name,
                workspace_slug=self.dbgap_workspace.workspace.name,
            )

    def test_invalid_billing_project_name(self):
        """Raises a 404 error with an invalid object dbgap_application_pk."""
        request = self.factory.get(self.get_url("foo", self.dbgap_workspace.workspace.name))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(
                request,
                billing_project_slug="foo",
                workspace_slug=self.dbgap_workspace.workspace.name,
            )

    def test_invalid_workspace_name(self):
        """Raises a 404 error with an invalid object dbgap_application_pk."""
        request = self.factory.get(self.get_url(self.dbgap_workspace.workspace.name, "foo"))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(
                request,
                billing_project_slug=self.dbgap_workspace.workspace.billing_project.name,
                workspace_slug="foo",
            )

    def test_context_data_access_audit(self):
        """The data_access_audit exists in the context."""
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("data_access_audit", response.context_data)
        data_access_audit = response.context_data["data_access_audit"]
        self.assertIsInstance(
            data_access_audit,
            audit.dbGaPAccessAudit,
        )
        self.assertTrue(data_access_audit.completed)
        self.assertEqual(data_access_audit.dbgap_workspace_queryset.count(), 1)
        self.assertIn(self.dbgap_workspace, data_access_audit.dbgap_workspace_queryset)

    def test_context_data_access_audit_does_not_include_other_applications(self):
        """The data_access_audit does not include other workspaces."""
        other_workspace = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        data_access_audit = response.context_data["data_access_audit"]
        self.assertEqual(data_access_audit.dbgap_workspace_queryset.count(), 1)
        self.assertNotIn(other_workspace, data_access_audit.dbgap_workspace_queryset)

    def test_context_verified_table_access(self):
        """verified_table shows a record when audit has verified access."""
        # Add a verified workspace.
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=self.dbgap_workspace)
        GroupGroupMembershipFactory.create(
            parent_group=self.dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), self.dbgap_workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.APPROVED_DAR,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_verified_table_no_snapshot(self):
        """verified_table shows a record when an application has no snapshots and no access."""
        factories.dbGaPApplicationFactory.create()
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), self.dbgap_workspace)
        self.assertIsNone(table.rows[0].get_cell_value("data_access_request"))
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.NO_SNAPSHOTS,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_verified_table_no_dar(self):
        """verified_table shows a record when an application has a snapshot, no dars, and no access."""
        factories.dbGaPDataAccessSnapshotFactory.create()
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), self.dbgap_workspace)
        self.assertIsNone(table.rows[0].get_cell_value("data_access_request"))
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.NO_DAR,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_verified_table_other_dar(self):
        """verified_table shows a record when there is no access and no matching dar."""
        other_dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=other_dbgap_workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), self.dbgap_workspace)
        self.assertIsNone(table.rows[0].get_cell_value("data_access_request"))
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.NO_DAR,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_verified_table_dar_not_approved(self):
        """verified_table shows a record when audit has verified no access."""
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=self.dbgap_workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), self.dbgap_workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.DAR_NOT_APPROVED,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_needs_action_table_grant(self):
        """needs_action_table shows a record when audit finds that access needs to be granted."""
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=self.dbgap_workspace)
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), self.dbgap_workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.NEW_APPROVED_DAR,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_needs_action_table_remove(self):
        """needs_action_table shows a record when audit finds that access needs to be removed."""
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=self.dbgap_workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        # Create an old dar that was approved
        old_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=False,
        )
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=dar.dbgap_dar_id,
            dbgap_data_access_snapshot=old_snapshot,
            dbgap_workspace=self.dbgap_workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        GroupGroupMembershipFactory.create(
            parent_group=self.dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), self.dbgap_workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.PREVIOUS_APPROVAL,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_error_table_has_access(self):
        """error shows a record when audit finds that access needs to be removed."""
        # Create a rejected DAR.
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=self.dbgap_workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        # Create the membership.
        GroupGroupMembershipFactory.create(
            parent_group=self.dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("errors_table", response.context_data)
        table = response.context_data["errors_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), self.dbgap_workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.ERROR_HAS_ACCESS,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_errors_table_no_snapshot_has_access(self):
        """errors_table has a record when an application has no snapshots but also has access."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Add the application group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=self.dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dbgap_application.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("errors_table", response.context_data)
        table = response.context_data["errors_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), self.dbgap_workspace)
        self.assertIsNone(table.rows[0].get_cell_value("data_access_request"))
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.ERROR_HAS_ACCESS,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_errors_table_no_dar_has_access(self):
        """errors_table has a record when an application has no DARs but also has access."""
        snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        # Add the application group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=self.dbgap_workspace.workspace.authorization_domains.first(),
            child_group=snapshot.dbgap_application.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.dbgap_workspace.workspace.billing_project.name,
                self.dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("errors_table", response.context_data)
        table = response.context_data["errors_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), self.dbgap_workspace)
        self.assertIsNone(table.rows[0].get_cell_value("data_access_request"))
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.ERROR_HAS_ACCESS,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))


class dbGaPAuditTest(TestCase):
    """Tests for the dbGaPAudit view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "dbgap:audit:all",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPAudit.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission_staff_view(self):
        """Returns successful response code if the user has staff view permission."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_status_code_with_user_permission_view(self):
        """Returns successful response code if the user has view permission."""
        user = User.objects.create_user(username="test-none", password="test-none")
        user.user_permissions.add(Permission.objects.get(codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME))
        request = self.factory.get(self.get_url())
        request.user = user
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url())
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_context_data_access_audit(self):
        """The data_access_audit exists in the context."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("data_access_audit", response.context_data)
        data_access_audit = response.context_data["data_access_audit"]
        self.assertIsInstance(
            data_access_audit,
            audit.dbGaPAccessAudit,
        )
        self.assertTrue(data_access_audit.completed)

    def test_no_applications_no_workspaces(self):
        """Loads correctly if there are no applications or workspaces."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        dbgap_audit = response.context_data["data_access_audit"]
        self.assertEqual(dbgap_audit.dbgap_application_queryset.count(), 0)
        self.assertEqual(dbgap_audit.dbgap_workspace_queryset.count(), 0)

    def test_one_applications_no_workspaces(self):
        """Loads correctly if there is one application and no workspaces."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        dbgap_audit = response.context_data["data_access_audit"]
        self.assertEqual(dbgap_audit.dbgap_application_queryset.count(), 1)
        self.assertIn(dbgap_application, dbgap_audit.dbgap_application_queryset)
        self.assertEqual(dbgap_audit.dbgap_workspace_queryset.count(), 0)
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)

    def test_no_applications_one_workspaces(self):
        """Loads correctly if there is no application one workspace."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        dbgap_audit = response.context_data["data_access_audit"]
        self.assertEqual(dbgap_audit.dbgap_application_queryset.count(), 0)
        self.assertEqual(dbgap_audit.dbgap_workspace_queryset.count(), 1)
        self.assertIn(dbgap_workspace, dbgap_audit.dbgap_workspace_queryset)
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)

    def test_three_applications_two_workspaces(self):
        """Loads correctly if there is one application and no workspaces."""
        dbgap_application_1 = factories.dbGaPApplicationFactory.create()
        dbgap_application_2 = factories.dbGaPApplicationFactory.create()
        dbgap_application_3 = factories.dbGaPApplicationFactory.create()
        dbgap_workspace_1 = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace_2 = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        dbgap_audit = response.context_data["data_access_audit"]
        self.assertEqual(dbgap_audit.dbgap_application_queryset.count(), 3)
        self.assertIn(dbgap_application_1, dbgap_audit.dbgap_application_queryset)
        self.assertIn(dbgap_application_2, dbgap_audit.dbgap_application_queryset)
        self.assertIn(dbgap_application_3, dbgap_audit.dbgap_application_queryset)
        self.assertEqual(dbgap_audit.dbgap_workspace_queryset.count(), 2)
        self.assertIn(dbgap_workspace_1, dbgap_audit.dbgap_workspace_queryset)
        self.assertIn(dbgap_workspace_2, dbgap_audit.dbgap_workspace_queryset)
        self.assertIn("verified_table", response.context_data)
        self.assertEqual(len(response.context_data["verified_table"].rows), 6)

    def test_context_verified_table_access(self):
        """verified_table shows a record when audit has verified access."""
        # Add a verified workspace.
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=workspace)
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.APPROVED_DAR,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_verified_table_no_access(self):
        """verified_table shows a record when audit has verified no access."""
        snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        workspace = factories.dbGaPWorkspaceFactory.create()
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("application"), snapshot.dbgap_application)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertIsNone(table.rows[0].get_cell_value("data_access_request"))
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.NO_DAR,
        )
        self.assertEqual(table.rows[0].get_cell_value("action"), "&mdash;")

    def test_context_needs_action_table_grant(self):
        """needs_action_table shows a record when audit finds that access needs to be granted."""
        workspace = factories.dbGaPWorkspaceFactory.create(created=timezone.now() - timedelta(weeks=4))
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=workspace)
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("application"),
            dar.dbgap_data_access_snapshot.dbgap_application,
        )
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.NEW_APPROVED_DAR,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_needs_action_table_remove(self):
        """needs_action_table shows a record when audit finds that access needs to be removed."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        # Create an old dar that was approved
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=dar.dbgap_dar_id,
            dbgap_data_access_snapshot__dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=4),
            dbgap_data_access_snapshot__is_most_recent=False,
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("application"),
            dar.dbgap_data_access_snapshot.dbgap_application,
        )
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.PREVIOUS_APPROVAL,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_error_table_has_access(self):
        """error shows a record when audit finds that access needs to be removed."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        # Create a rejected DAR.
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        # Create the membership.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("errors_table", response.context_data)
        table = response.context_data["errors_table"]
        self.assertIsInstance(
            table,
            audit.dbGaPAccessAuditTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertEqual(table.rows[0].get_cell_value("data_access_request"), dar)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.dbGaPAccessAudit.ERROR_HAS_ACCESS,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))


class dbGaPAuditResolveTest(AnVILAPIMockTestMixin, TestCase):
    """Tests for the dbGaPAudit view."""

    def setUp(self):
        """Set up test class."""
        super().setUp()
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME)
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "dbgap:audit:resolve",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPAuditResolve.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(1, "foo", "bar"))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(1, "foo", "bar"),
        )

    def test_status_code_with_user_permission_staff_edit(self):
        """Returns successful response code if the user has staff edit permission."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                dbgap_application.dbgap_project_id,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_status_code_with_user_permission_staff_view(self):
        """Returns 403 response code if the user has staff view permission."""
        user_view = User.objects.create_user(username="test-view", password="test-view")
        user_view.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )
        self.client.force_login(self.user)
        request = self.factory.get(self.get_url(1, "foo", "bar"))
        request.user = user_view
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_status_code_with_user_permission_view(self):
        """Returns forbidden response code if the user has view permission."""
        user = User.objects.create_user(username="test-none", password="test-none")
        user.user_permissions.add(Permission.objects.get(codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME))
        request = self.factory.get(self.get_url(1, "foo", "bar"))
        request.user = user
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(username="test-none", password="test-none")
        request = self.factory.get(self.get_url(1, "foo", "bar"))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request)

    def test_dbgap_application_does_not_exist(self):
        """Raises a 404 error with an invalid object dbgap_application_pk."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                1,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_billing_project_does_not_exist(self):
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        request = self.factory.get(
            self.get_url(
                dbgap_application.dbgap_project_id,
                "foo",
                dbgap_workspace.workspace.name,
            )
        )
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request)

    def test_workspace_does_not_exist(self):
        dbgap_application = factories.dbGaPApplicationFactory.create()
        billing_project = BillingProjectFactory.create()
        request = self.factory.get(self.get_url(dbgap_application.dbgap_project_id, billing_project.name, "foo"))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request)

    def test_get_context_audit_result(self):
        """The data_access_audit exists in the context."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                dbgap_application.dbgap_project_id,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("audit_result", response.context_data)
        self.assertIsInstance(
            response.context_data["audit_result"],
            audit.AuditResult,
        )

    def test_get_context_dbgap_application(self):
        """The dbgap_application exists in the context."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                dbgap_application.dbgap_project_id,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("dbgap_application", response.context_data)
        self.assertEqual(response.context_data["dbgap_application"], dbgap_application)

    def test_get_context_dbgap_workspace(self):
        """The dbgap_workspace exists in the context."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                dbgap_application.dbgap_project_id,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            )
        )
        self.assertIn("dbgap_workspace", response.context_data)
        self.assertEqual(response.context_data["dbgap_workspace"], dbgap_workspace)

    def test_get_verified_access(self):
        """Get request with verified access."""
        # Add a verified workspace.
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=workspace)
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            )
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, audit.VerifiedAccess)
        self.assertEqual(audit_result.workspace, workspace)
        self.assertEqual(
            audit_result.dbgap_application,
            dar.dbgap_data_access_snapshot.dbgap_application,
        )
        self.assertEqual(audit_result.data_access_request, dar)
        self.assertEqual(
            audit_result.note,
            audit.dbGaPAccessAudit.APPROVED_DAR,
        )
        self.assertIsNone(audit_result.action)

    def test_get_verified_no_access(self):
        """verified_table shows a record when audit has verified no access."""
        snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        workspace = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            )
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, audit.VerifiedNoAccess)
        self.assertEqual(audit_result.workspace, workspace)
        self.assertEqual(audit_result.dbgap_application, snapshot.dbgap_application)
        self.assertIsNone(audit_result.data_access_request)
        self.assertEqual(
            audit_result.note,
            audit.dbGaPAccessAudit.NO_DAR,
        )
        self.assertIsNone(audit_result.action)

    def test_get_grant_access(self):
        """needs_action_table shows a record when audit finds that access needs to be granted."""
        workspace = factories.dbGaPWorkspaceFactory.create(created=timezone.now() - timedelta(weeks=4))
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=workspace)
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            )
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, audit.GrantAccess)
        self.assertEqual(audit_result.workspace, workspace)
        self.assertEqual(
            audit_result.dbgap_application,
            dar.dbgap_data_access_snapshot.dbgap_application,
        )
        self.assertEqual(audit_result.data_access_request, dar)
        self.assertEqual(
            audit_result.note,
            audit.dbGaPAccessAudit.NEW_APPROVED_DAR,
        )
        self.assertIsNotNone(audit_result.action)

    def test_get_remove_access(self):
        """needs_action_table shows a record when audit finds that access needs to be removed."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        # Create an old dar that was approved
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=dar.dbgap_dar_id,
            dbgap_data_access_snapshot__dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=4),
            dbgap_data_access_snapshot__is_most_recent=False,
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            )
        )
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, audit.RemoveAccess)
        self.assertEqual(audit_result.workspace, workspace)
        self.assertEqual(
            audit_result.dbgap_application,
            dar.dbgap_data_access_snapshot.dbgap_application,
        )
        self.assertEqual(audit_result.data_access_request, dar)
        self.assertEqual(
            audit_result.note,
            audit.dbGaPAccessAudit.PREVIOUS_APPROVAL,
        )
        self.assertIsNotNone(audit_result.action)

    def test_post_verified_access(self):
        """post with VerifiedAccess audit result."""
        # Add a verified workspace.
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=workspace)
        date_created = timezone.now() - timedelta(weeks=3)
        with freeze_time(date_created):
            membership = GroupGroupMembershipFactory.create(
                parent_group=workspace.workspace.authorization_domains.first(),
                child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
            )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            ),
            {},
        )
        self.assertRedirects(response, reverse("dbgap:audit:all"))
        # Membership hasn't changed.
        membership.refresh_from_db()
        self.assertEqual(membership.created, date_created)
        self.assertEqual(membership.parent_group, workspace.workspace.authorization_domains.first())
        self.assertEqual(
            membership.child_group,
            dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )

    def test_post_verified_no_access(self):
        """post with VerifiedNoAccess audit result."""
        snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        workspace = factories.dbGaPWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            ),
            {},
        )
        self.assertRedirects(response, reverse("dbgap:audit:all"))
        # No membership has been created.
        self.assertEqual(GroupGroupMembership.objects.count(), 0)

    def test_post_grant_access(self):
        """post with GrantAccess audit result."""
        workspace = factories.dbGaPWorkspaceFactory.create(workspace__name="TEST_DBGAP")
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=workspace,
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        group_name = dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group.name
        api_url = self.api_client.sam_entry_point + f"/api/groups/v1/auth_TEST_DBGAP/member/{group_name}@firecloud.org"
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=204,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            ),
            {},
        )
        # The GroupGroup membership was created.
        self.assertRedirects(response, reverse("dbgap:audit:all"))
        membership = GroupGroupMembership.objects.get(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        self.assertEqual(membership.role, membership.MEMBER)

    def test_post_grant_access_htmx(self):
        """Context with GrantAccess."""
        workspace = factories.dbGaPWorkspaceFactory.create(workspace__name="TEST_DBGAP")
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=workspace,
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        group_name = dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group.name
        api_url = self.api_client.sam_entry_point + f"/api/groups/v1/auth_TEST_DBGAP/member/{group_name}@firecloud.org"
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=204,
        )
        self.client.force_login(self.user)
        header = {"HTTP_HX-Request": "true"}
        response = self.client.post(
            self.get_url(
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            ),
            {},
            **header,
        )
        self.assertEqual(response.content.decode(), views.dbGaPAuditResolve.htmx_success)
        # Membership has been created.
        membership = GroupGroupMembership.objects.get(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        self.assertEqual(membership.role, membership.MEMBER)

    def test_post_remove_access(self):
        """needs_action_table shows a record when audit finds that access needs to be removed."""
        workspace = factories.dbGaPWorkspaceFactory.create(workspace__name="TEST_DBGAP")
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        # Create an old dar that was approved
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=dar.dbgap_dar_id,
            dbgap_data_access_snapshot__dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=4),
            dbgap_data_access_snapshot__is_most_recent=False,
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        membership = GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        group_name = dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group.name
        api_url = self.api_client.sam_entry_point + f"/api/groups/v1/auth_TEST_DBGAP/member/{group_name}@firecloud.org"
        self.anvil_response_mock.add(
            responses.DELETE,
            api_url,
            status=204,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            ),
            {},
        )
        self.assertRedirects(response, reverse("dbgap:audit:all"))
        # Make sure the membership has been deleted.
        with self.assertRaises(GroupGroupMembership.DoesNotExist):
            membership.refresh_from_db()

    def test_anvil_api_error_grant(self):
        """AnVIL API errors are properly handled."""
        workspace = factories.dbGaPWorkspaceFactory.create(workspace__name="TEST_DBGAP")
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=workspace,
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        group_name = dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group.name
        api_url = self.api_client.sam_entry_point + f"/api/groups/v1/auth_TEST_DBGAP/member/{group_name}@firecloud.org"
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            ),
            {},
        )
        self.assertEqual(response.status_code, 200)
        # No group membership was created.
        self.assertEqual(GroupGroupMembership.objects.count(), 0)
        # Audit result is still GrantAccess.
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, audit.GrantAccess)
        # A message was added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertIn("AnVIL API Error", str(messages[0]))

    def test_anvil_api_error_grant_htmx(self):
        """AnVIL API errors are properly handled with htmx."""
        workspace = factories.dbGaPWorkspaceFactory.create(workspace__name="TEST_DBGAP")
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=workspace,
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        group_name = dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group.name
        api_url = self.api_client.sam_entry_point + f"/api/groups/v1/auth_TEST_DBGAP/member/{group_name}@firecloud.org"
        self.anvil_response_mock.add(
            responses.PUT,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        # Check the response.
        self.client.force_login(self.user)
        header = {"HTTP_HX-Request": "true"}
        response = self.client.post(
            self.get_url(
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            ),
            {},
            **header,
        )
        self.assertEqual(response.content.decode(), views.dbGaPAuditResolve.htmx_error)
        # No group membership was created.
        self.assertEqual(GroupGroupMembership.objects.count(), 0)
        # No messages were added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 0)

    def test_anvil_api_error_remove(self):
        """AnVIL API errors are properly handled."""
        workspace = factories.dbGaPWorkspaceFactory.create(workspace__name="TEST_DBGAP")
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        # Create an old dar that was approved
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=dar.dbgap_dar_id,
            dbgap_data_access_snapshot__dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=4),
            dbgap_data_access_snapshot__is_most_recent=False,
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        membership = GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        group_name = dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group.name
        api_url = self.api_client.sam_entry_point + f"/api/groups/v1/auth_TEST_DBGAP/member/{group_name}@firecloud.org"
        self.anvil_response_mock.add(
            responses.DELETE,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            ),
            {},
        )
        self.assertEqual(response.status_code, 200)
        # The group-group membership still exists.
        membership.refresh_from_db()
        # Audit result is still RemoveAccess.
        self.assertIn("audit_result", response.context_data)
        audit_result = response.context_data["audit_result"]
        self.assertIsInstance(audit_result, audit.RemoveAccess)
        # A message was added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 1)
        self.assertIn("AnVIL API Error", str(messages[0]))

    def test_anvil_api_error_remove_htmx(self):
        """AnVIL API errors are properly handled."""
        workspace = factories.dbGaPWorkspaceFactory.create(workspace__name="TEST_DBGAP")
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        # Create an old dar that was approved
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=dar.dbgap_dar_id,
            dbgap_data_access_snapshot__dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=4),
            dbgap_data_access_snapshot__is_most_recent=False,
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        membership = GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        # Add API response
        # Note that the auth domain group is created automatically by the factory using the workspace name.
        group_name = dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group.name
        api_url = self.api_client.sam_entry_point + f"/api/groups/v1/auth_TEST_DBGAP/member/{group_name}@firecloud.org"
        self.anvil_response_mock.add(
            responses.DELETE,
            api_url,
            status=500,
            json=ErrorResponseFactory().response,
        )
        self.client.force_login(self.user)
        header = {"HTTP_HX-Request": "true"}
        response = self.client.post(
            self.get_url(
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
            ),
            {},
            **header,
        )
        self.assertEqual(response.content.decode(), views.dbGaPAuditResolve.htmx_error)
        # The group-group membership still exists.
        membership.refresh_from_db()
        # No messages was added.
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(len(messages), 0)


class dbGaPRecordsIndexTest(TestCase):
    """Tests for the dbGaPRecordsIndex view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:records:index", args=args)

    def test_status_code_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_status_code_user_logged_in(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_links(self):
        """response includes the correct links."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertContains(response, reverse("dbgap:records:applications"))
        # In case we add similar public views later.
        # self.assertContains(response, reverse("cdsa:records:user_access"))
        # self.assertContains(response, reverse("cdsa:records:workspaces"))


class dbGaPApplicationRecordsListTest(TestCase):
    """Tests for the dbGaPApplicationRecordsList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("dbgap:records:applications", args=args)

    def test_status_code_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_status_code_user_logged_in(self):
        """Returns successful response code."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)

    def test_table_class(self):
        """The table is the correct class."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertIsInstance(response.context_data["table"], tables.dbGaPApplicationRecordsTable)

    def test_table_no_rows(self):
        """No rows are shown if there are no dbGaPApplications objects."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_table_three_rows(self):
        """Three rows are shown if there are three dbGaPApplication objects."""
        factories.dbGaPApplicationFactory.create_batch(3)
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 3)
