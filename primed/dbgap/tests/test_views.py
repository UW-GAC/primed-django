"""Tests for views related to the `dbgap` app."""

import json

import responses
from anvil_consortium_manager import views as acm_views
from anvil_consortium_manager.models import (
    AnVILProjectManagerAccess,
    ManagedGroup,
    Workspace,
)
from anvil_consortium_manager.tests.factories import (
    BillingProjectFactory,
    ManagedGroupFactory,
)
from anvil_consortium_manager.tests.utils import AnVILAPIMockTestMixin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase
from django.urls import reverse
from faker import Faker

from primed.primed_anvil.tests.factories import (
    DataUseModifierFactory,
    DataUsePermissionFactory,
    StudyFactory,
)
from primed.users.tests.factories import UserFactory

from .. import forms, models, tables, views
from . import factories

fake = Faker()

User = get_user_model()


class dbGaPStudyAccessionListTest(TestCase):
    """Tests for the dbGaPStudyAccessionList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
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
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
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
        self.assertIsInstance(
            response.context_data["table"], tables.dbGaPStudyAccessionTable
        )

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
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
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
        response = self.client.get(self.get_url(self.obj.pk))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(self.obj.pk),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, pk=self.obj.pk)

    def test_view_status_code_with_existing_object(self):
        """Returns a successful status code for an existing object pk."""
        # Only clients load the template.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.pk))
        self.assertEqual(response.status_code, 200)

    def test_view_status_code_with_invalid_pk(self):
        """Raises a 404 error with an invalid object pk."""
        request = self.factory.get(self.get_url(self.obj.pk + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, pk=self.obj.pk + 1)

    def test_workspace_table(self):
        """The workspace table exists."""
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("workspace_table", response.context_data)
        self.assertIsInstance(
            response.context_data["workspace_table"], tables.dbGaPWorkspaceTable
        )

    def test_workspace_table_none(self):
        """No workspaces are shown if the dbGaPStudyAccession does not have any workspaces."""
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("workspace_table", response.context_data)
        self.assertEqual(len(response.context_data["workspace_table"].rows), 0)

    def test_workspace_table_one(self):
        """One workspace is shown if the dbGaPStudyAccession has one workspace."""
        factories.dbGaPWorkspaceFactory.create(dbgap_study_accession=self.obj)
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("workspace_table", response.context_data)
        self.assertEqual(len(response.context_data["workspace_table"].rows), 1)

    def test_workspace_table_two(self):
        """Two workspaces are shown if the dbGaPStudyAccession has two workspaces."""
        factories.dbGaPWorkspaceFactory.create_batch(2, dbgap_study_accession=self.obj)
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("workspace_table", response.context_data)
        self.assertEqual(len(response.context_data["workspace_table"].rows), 2)

    def test_shows_workspace_for_only_this_dbGaPStudyAccession(self):
        """Only shows workspaces for this dbGaPStudyAccession."""
        other_dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession=other_dbgap_study_accession
        )
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("workspace_table", response.context_data)
        self.assertEqual(len(response.context_data["workspace_table"].rows), 0)


class dbGaPStudyAccessionCreateTest(TestCase):
    """Tests for the dbGaPStudyAccessionCreate view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.StudyFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
            )
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
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
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

    def test_form_class(self):
        """Form is the expected class."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIsInstance(
            response.context_data["form"], forms.dbGaPStudyAccessionForm
        )

    def test_can_create_object(self):
        """Can create an object."""
        self.client.force_login(self.user)
        study = StudyFactory.create()
        response = self.client.post(self.get_url(), {"study": study.pk, "phs": 1})
        self.assertEqual(response.status_code, 302)
        # A new object was created.
        self.assertEqual(models.dbGaPStudyAccession.objects.count(), 1)
        new_object = models.dbGaPStudyAccession.objects.latest("pk")
        self.assertEqual(new_object.study, study)
        self.assertEqual(new_object.phs, 1)

    def test_redirect_url(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        study = StudyFactory.create()
        response = self.client.post(self.get_url(), {"study": study.pk, "phs": 1})
        new_object = models.dbGaPStudyAccession.objects.latest("pk")
        self.assertRedirects(response, new_object.get_absolute_url())

    def test_success_message(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        study = StudyFactory.create()
        response = self.client.post(
            self.get_url(),
            {"study": study.pk, "phs": 1},
            follow=True,
        )
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(views.dbGaPStudyAccessionCreate.success_msg, str(messages[0]))

    def test_error_missing_study(self):
        """Form shows an error when study is missing."""
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"phs": 1})
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPStudyAccession.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("study", form.errors)
        self.assertEqual(len(form.errors["study"]), 1)
        self.assertIn("required", form.errors["study"][0])

    def test_error_missing_phs(self):
        """Form shows an error when phs is missing."""
        self.client.force_login(self.user)
        study = StudyFactory.create()
        response = self.client.post(self.get_url(), {"study": study.pk})
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPStudyAccession.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("phs", form.errors)
        self.assertEqual(len(form.errors["phs"]), 1)
        self.assertIn("required", form.errors["phs"][0])

    def test_error_duplicate_short_name(self):
        """Form shows an error when trying to create a duplicate phs."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        other_study = factories.StudyFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(), {"phs": dbgap_study_accession.phs, "study": other_study.pk}
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPStudyAccession.objects.count(), 1)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("phs", form.errors)
        self.assertEqual(len(form.errors["phs"]), 1)
        self.assertIn("already exists", form.errors["phs"][0])

    def test_post_blank_data(self):
        """Posting blank data does not create an object."""
        request = self.factory.post(self.get_url(), {})
        request.user = self.user
        response = self.get_view()(request)
        self.assertEqual(response.status_code, 200)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 2)
        self.assertIn("study", form.errors.keys())
        self.assertEqual(len(form.errors["study"]), 1)
        self.assertIn("required", form.errors["study"][0])
        self.assertIn("phs", form.errors.keys())
        self.assertEqual(len(form.errors["phs"]), 1)
        self.assertIn("required", form.errors["phs"][0])
        self.assertEqual(models.dbGaPStudyAccession.objects.count(), 0)


class dbGaPWorkspaceListTest(TestCase):
    """Tests of the anvil_consortium_manager WorkspaceList view using this app's dbGaPWorkspaceAdapter."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
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
        self.assertIsInstance(
            response.context_data["table"], tables.dbGaPWorkspaceTable
        )


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
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
            )
        )
        self.workspace_type = "dbgap"

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:workspaces:new", args=args)

    def get_api_url(self, billing_project_name, workspace_name):
        """Return the Terra API url for a given billing project and workspace."""
        return (
            self.entry_point
            + "/api/workspaces/"
            + billing_project_name
            + "/"
            + workspace_name
        )

    def test_creates_upload_workspace(self):
        """Posting valid data to the form creates a workspace data object when using a custom adapter."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        data_use_permission = DataUsePermissionFactory.create()
        data_use_modifier_1 = DataUseModifierFactory.create()
        data_use_modifier_2 = DataUseModifierFactory.create()
        # Create an extra that won't be specified.
        DataUseModifierFactory.create()
        billing_project = BillingProjectFactory.create(name="test-billing-project")
        url = self.entry_point + "/api/workspaces"
        json_data = {
            "namespace": "test-billing-project",
            "name": "test-workspace",
            "attributes": {},
        }
        responses.add(
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
                "workspacedata-0-data_use_permission": data_use_permission.pk,
                "workspacedata-0-data_use_modifiers": [
                    data_use_modifier_1.pk,
                    data_use_modifier_2.pk,
                ],
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.dbGaPWorkspace.objects.count(), 1)
        new_workspace_data = models.dbGaPWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(
            new_workspace_data.dbgap_study_accession, dbgap_study_accession
        )
        self.assertEqual(new_workspace_data.dbgap_version, 2)
        self.assertEqual(new_workspace_data.dbgap_participant_set, 3)
        self.assertEqual(new_workspace_data.dbgap_consent_abbreviation, "GRU-TEST")
        self.assertEqual(new_workspace_data.dbgap_consent_code, 4)
        self.assertEqual(new_workspace_data.data_use_limitations, "test limitations")
        self.assertEqual(new_workspace_data.data_use_permission, data_use_permission)
        self.assertEqual(new_workspace_data.data_use_modifiers.count(), 2)
        self.assertIn(data_use_modifier_1, new_workspace_data.data_use_modifiers.all())
        self.assertIn(data_use_modifier_2, new_workspace_data.data_use_modifiers.all())
        responses.assert_call_count(url, 1)


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
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
            )
        )
        self.workspace_type = "dbgap"

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:workspaces:import", args=args)

    def get_api_url(self, billing_project_name, workspace_name):
        """Return the Terra API url for a given billing project and workspace."""
        return (
            self.entry_point
            + "/api/workspaces/"
            + billing_project_name
            + "/"
            + workspace_name
        )

    def get_api_json_response(
        self, billing_project, workspace, authorization_domains=[], access="OWNER"
    ):
        """Return a pared down version of the json response from the AnVIL API with only fields we need."""
        json_data = {
            "accessLevel": access,
            "owners": [],
            "workspace": {
                "authorizationDomain": [
                    {"membersGroupName": x} for x in authorization_domains
                ],
                "name": workspace,
                "namespace": billing_project,
            },
        }
        return json_data

    def test_creates_dbgap_workspace(self):
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
        workspace_list_url = self.entry_point + "/api/workspaces"
        responses.add(
            responses.GET,
            workspace_list_url,
            match=[
                responses.matchers.query_param_matcher(
                    {"fields": "workspace.namespace,workspace.name,accessLevel"}
                )
            ],
            status=200,
            json=[self.get_api_json_response(billing_project.name, workspace_name)],
        )
        url = self.get_api_url(billing_project.name, workspace_name)
        responses.add(
            responses.GET,
            url,
            status=self.api_success_code,
            json=self.get_api_json_response(billing_project.name, workspace_name),
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
                "workspacedata-0-data_use_permission": data_use_permission.pk,
                "workspacedata-0-data_use_modifiers": [
                    data_use_modifier_1.pk,
                    data_use_modifier_2.pk,
                ],
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.dbGaPWorkspace.objects.count(), 1)
        new_workspace_data = models.dbGaPWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(
            new_workspace_data.dbgap_study_accession, dbgap_study_accession
        )
        self.assertEqual(new_workspace_data.dbgap_version, 2)
        self.assertEqual(new_workspace_data.dbgap_participant_set, 3)
        self.assertEqual(new_workspace_data.dbgap_consent_abbreviation, "GRU-TEST")
        self.assertEqual(new_workspace_data.dbgap_consent_code, 4)
        self.assertEqual(new_workspace_data.data_use_limitations, "test limitations")
        self.assertEqual(new_workspace_data.data_use_permission, data_use_permission)
        self.assertEqual(new_workspace_data.data_use_modifiers.count(), 2)
        self.assertIn(data_use_modifier_1, new_workspace_data.data_use_modifiers.all())
        self.assertIn(data_use_modifier_2, new_workspace_data.data_use_modifiers.all())
        responses.assert_call_count(url, 1)


class dbGaPApplicationListTest(TestCase):
    """Tests for the ApplicationList view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
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
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
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
        self.assertIsInstance(
            response.context_data["table"], tables.dbGaPApplicationTable
        )

    def test_workspace_table_none(self):
        """No rows are shown if there are no dbGaPApplication objects."""
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 0)

    def test_workspace_table_one(self):
        """One row is shown if there is one dbGaPApplication."""
        factories.dbGaPApplicationFactory.create()
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 1)

    def test_workspace_table_two(self):
        """Two rows are shown if there are two dbGaPApplication objects."""
        factories.dbGaPApplicationFactory.create_batch(2)
        request = self.factory.get(self.get_url())
        request.user = self.user
        response = self.get_view()(request)
        self.assertIn("table", response.context_data)
        self.assertEqual(len(response.context_data["table"].rows), 2)


class dbGaPApplicationDetailTest(TestCase):
    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
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
        response = self.client.get(self.get_url(self.obj.pk))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(self.obj.pk),
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, pk=self.obj.pk)

    def test_view_status_code_with_existing_object(self):
        """Returns a successful status code for an existing object pk."""
        # Only clients load the template.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.obj.pk))
        self.assertEqual(response.status_code, 200)

    def test_view_status_code_with_invalid_pk(self):
        """Raises a 404 error with an invalid object pk."""
        request = self.factory.get(self.get_url(self.obj.pk + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, pk=self.obj.pk + 1)

    def test_workspace_table(self):
        """The data_access_request_table exists."""
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("data_access_request_table", response.context_data)
        self.assertIsInstance(
            response.context_data["data_access_request_table"],
            tables.dbGaPDataAccessRequestTable,
        )

    def test_dar_table_none(self):
        """No dbGaPDataAccessRequests are shown if the dbGaPApplication does not have any DARs."""
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("data_access_request_table", response.context_data)
        self.assertEqual(
            len(response.context_data["data_access_request_table"].rows), 0
        )

    def test_dar_table_one(self):
        """One dbGaPDataAccessRequest is shown if the dbGaPApplication has one DAR."""
        factories.dbGaPDataAccessRequestFactory.create(dbgap_application=self.obj)
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("data_access_request_table", response.context_data)
        self.assertEqual(
            len(response.context_data["data_access_request_table"].rows), 1
        )

    def test_dar_table_two(self):
        """Two dbGaPDataAccessRequests are shown if the dbGaPApplication has two DARs."""
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2, dbgap_application=self.obj
        )
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("data_access_request_table", response.context_data)
        self.assertEqual(
            len(response.context_data["data_access_request_table"].rows), 2
        )

    def test_shows_dar_for_only_this_dbGaPApplication(self):
        """Only shows workspaces for this dbGaPApplication."""
        other_dbgap_application = factories.dbGaPApplicationFactory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=other_dbgap_application
        )
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("data_access_request_table", response.context_data)
        self.assertEqual(
            len(response.context_data["data_access_request_table"].rows), 0
        )

    def test_context_show_add_dars_button_no_dars(self):
        """The show_add_dars_button is True in context when there are no DARs for this application."""
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("show_add_dars_button", response.context_data)
        self.assertTrue(response.context_data["show_add_dars_button"])

    def test_context_show_add_dars_button_dars_with_dars(self):
        """The show_add_dars_button is False in context when there are DARs for this application."""
        factories.dbGaPDataAccessRequestFactory.create(dbgap_application=self.obj)
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("show_add_dars_button", response.context_data)
        self.assertFalse(response.context_data["show_add_dars_button"])

    def test_context_show_add_dars_button_other_dars(self):
        """show_add_dars_button in context is True when there are only DARs associated with a different application."""
        other_application = factories.dbGaPApplicationFactory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=other_application
        )
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("show_add_dars_button", response.context_data)
        self.assertTrue(response.context_data["show_add_dars_button"])

    def test_context_show_dars_no_dars(self):
        """show_dars in context is False when there are no DARs for this application."""
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("show_dars", response.context_data)
        self.assertFalse(response.context_data["show_dars"])

    def test_context_show_dars_dars_not_approved(self):
        """show_dars in context is True when there are only DARs that are not approved."""
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=self.obj,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=self.obj,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=self.obj,
            dbgap_current_status=models.dbGaPDataAccessRequest.EXPIRED,
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=self.obj,
            dbgap_current_status=models.dbGaPDataAccessRequest.NEW,
        )
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("show_dars", response.context_data)
        self.assertTrue(response.context_data["show_dars"])

    def test_context_show_dars_dars_with_dars(self):
        """show_dars in context is True when there are DARs for this application."""
        factories.dbGaPDataAccessRequestFactory.create(dbgap_application=self.obj)
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("show_dars", response.context_data)
        self.assertTrue(response.context_data["show_dars"])

    def test_context_show_dars_other_dars(self):
        """show_dars in context is False when there are DARs associated with a different application."""
        factories.dbGaPDataAccessRequestFactory.create()
        request = self.factory.get(self.get_url(self.obj.pk))
        request.user = self.user
        response = self.get_view()(request, pk=self.obj.pk)
        self.assertIn("show_dars", response.context_data)
        self.assertFalse(response.context_data["show_dars"])


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
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
            )
        )

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
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
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
        # API response to create the associated anvil_group.
        api_url = self.entry_point + "/api/groups/PRIMED_DBGAP_ACCESS_1"
        responses.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        response = self.client.post(
            self.get_url(), {"principal_investigator": pi.pk, "project_id": 1}
        )
        self.assertEqual(response.status_code, 302)
        # A new object was created.
        self.assertEqual(models.dbGaPApplication.objects.count(), 1)
        new_object = models.dbGaPApplication.objects.latest("pk")
        self.assertEqual(new_object.principal_investigator, pi)
        self.assertEqual(new_object.project_id, 1)

    def test_redirect_url(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_group.
        api_url = self.entry_point + "/api/groups/PRIMED_DBGAP_ACCESS_1"
        responses.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        response = self.client.post(
            self.get_url(), {"principal_investigator": pi.pk, "project_id": 1}
        )
        new_object = models.dbGaPApplication.objects.latest("pk")
        self.assertRedirects(response, new_object.get_absolute_url())

    def test_success_message(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_group.
        api_url = self.entry_point + "/api/groups/PRIMED_DBGAP_ACCESS_1"
        responses.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        response = self.client.post(
            self.get_url(),
            {"principal_investigator": pi.pk, "project_id": 1},
            follow=True,
        )
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(views.dbGaPApplicationCreate.success_msg, str(messages[0]))

    def test_error_missing_pi(self):
        """Form shows an error when principal_investigator is missing."""
        self.client.force_login(self.user)
        response = self.client.post(self.get_url(), {"project_id": 1})
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
            {"principal_investigator": self.user.pk + 1, "project_id": 12345},
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
        """Form shows an error when phs is missing."""
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
        self.assertIn("project_id", form.errors)
        self.assertEqual(len(form.errors["project_id"]), 1)
        self.assertIn("required", form.errors["project_id"][0])

    def test_error_duplicate_project_id(self):
        """Form shows an error when trying to create a duplicate phs."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        other_pi = UserFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(),
            {
                "principal_investigator": other_pi.pk,
                "project_id": dbgap_application.project_id,
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
        self.assertIn("project_id", form.errors)
        self.assertEqual(len(form.errors["project_id"]), 1)
        self.assertIn("already exists", form.errors["project_id"][0])

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
        self.assertIn("project_id", form.errors.keys())
        self.assertEqual(len(form.errors["project_id"]), 1)
        self.assertIn("required", form.errors["project_id"][0])
        self.assertEqual(models.dbGaPApplication.objects.count(), 0)

    def test_creates_anvil_group(self):
        """View creates a managed group upon when form is valid."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_group.
        api_url = self.entry_point + "/api/groups/PRIMED_DBGAP_ACCESS_12498"
        responses.add(
            responses.POST, api_url, status=201, json={"message": "mock message"}
        )
        response = self.client.post(
            self.get_url(), {"principal_investigator": pi.pk, "project_id": 12498}
        )
        self.assertEqual(response.status_code, 302)
        new_object = models.dbGaPApplication.objects.latest("pk")
        self.assertEqual(ManagedGroup.objects.count(), 1)
        # A new group was created.
        new_group = ManagedGroup.objects.latest("pk")
        self.assertEqual(new_object.anvil_group, new_group)
        self.assertEqual(new_group.name, "PRIMED_DBGAP_ACCESS_12498")
        self.assertTrue(new_group.is_managed_by_app)

    def test_manage_group_create_api_error(self):
        """Nothing is created when the form is valid but there is an API error when creating the group."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # API response to create the associated anvil_group.
        api_url = self.entry_point + "/api/groups/PRIMED_DBGAP_ACCESS_1"
        responses.add(
            responses.POST, api_url, status=500, json={"message": "other error"}
        )
        response = self.client.post(
            self.get_url(), {"principal_investigator": pi.pk, "project_id": 1}
        )
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
        self.assertEqual(ManagedGroup.objects.count(), 0)

    def test_managed_group_already_exists_in_app(self):
        """No objects are created if the managed group already exists in the app."""
        self.client.force_login(self.user)
        pi = UserFactory.create()
        # Create a group with the same name.
        ManagedGroupFactory.create(name="PRIMED_DBGAP_ACCESS_1")
        response = self.client.post(
            self.get_url(), {"principal_investigator": pi.pk, "project_id": 1}
        )
        self.assertEqual(response.status_code, 200)
        # The form is valid...
        form = response.context["form"]
        self.assertTrue(form.is_valid())
        # ...but there was an error with the group name.
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.dbGaPApplicationCreate.ERROR_CREATING_GROUP, str(messages[0])
        )
        # No dbGaPApplication was created.
        self.assertEqual(models.dbGaPApplication.objects.count(), 0)


class dbGaPDataAccessRequestCreateFromJsonTest(TestCase):
    """Tests for the dbGaPDataAccessRequestCreateFromJson view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        self.model_factory = factories.StudyFactory
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
            )
        )
        self.dbgap_application = factories.dbGaPApplicationFactory.create()
        self.pi_name = fake.name()
        self.json = {
            "Project_id": self.dbgap_application.project_id,
            "PI_name": self.pi_name,
            "Project_closed": "no",
            "studies": [],
        }
        self.study_accession = factories.dbGaPStudyAccessionFactory.create()
        self.valid_json = [
            {
                "Project_id": self.dbgap_application.project_id,
                "PI_name": "Test Investigator",
                "Project_closed": "no",
                # Two studies.
                "studies": [
                    {
                        "study_name": "Test study 1",
                        "study_accession": "phs{phs:06d}".format(
                            phs=self.study_accession.phs
                        ),
                        "requests": [
                            {
                                "DAC_abbrev": "FOOBI",
                                "consent_abbrev": "GRU",
                                "consent_code": 1,
                                "DAR": 23497,
                                "current_version": 12,
                                "current_DAR_status": "approved",
                                "was_approved": "yes",
                            },
                        ],
                    },
                ],
            }
        ]
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            match=[
                responses.matchers.query_param_matcher(
                    {"study_id": "phs{phs:06d}".format(phs=self.study_accession.phs)}
                )
            ],
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs000421.v32.p18"
            },
        )

    def add_json_study(self, study_accession, requests=[]):
        study_json = {
            "study_name": fake.company(),
            "study_accession": "phs{phs:06d}".format(phs=study_accession),
            "requests": requests,
        }
        self.json["studies"] = self.json["studies"] + [study_json]

    def get_request_json(
        self, dar_id, consent_abbreviation, consent_code, status="approved"
    ):
        """Returns a pared back version of the DAR JSON for a single consent group that is needed for the view."""
        request_json = {
            "DAR": dar_id,
            "consent_abbrev": consent_abbreviation,
            "consent_code": consent_code,
            "current_DAR_status": status,
        }
        return request_json

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "dbgap:dbgap_applications:dbgap_data_access_requests:new_from_json",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.dbGaPDataAccessRequestCreateFromJson.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url(self.dbgap_application.pk))
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL)
            + "?next="
            + self.get_url(self.dbgap_application.pk),
        )

    def test_status_code_with_user_permission_edit(self):
        """Returns successful response code."""
        request = self.factory.get(self.get_url(self.dbgap_application.pk))
        request.user = self.user
        response = self.get_view()(
            request, dbgap_application_pk=self.dbgap_application.pk
        )
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(self.get_url(self.dbgap_application.pk))
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, dbgap_application_pk=self.dbgap_application.pk)

    def test_access_without_user_permission_view(self):
        """Raises permission denied if user has no permissions."""
        user_view_perm = User.objects.create_user(
            username="test-none", password="test-none"
        )
        user_view_perm.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        request = self.factory.get(self.get_url(self.dbgap_application.pk))
        request.user = user_view_perm
        with self.assertRaises(PermissionDenied):
            self.get_view()(request, dbgap_application_pk=self.dbgap_application.pk)

    def test_has_form_in_context(self):
        """Response includes a form."""
        request = self.factory.get(self.get_url(self.dbgap_application.pk))
        request.user = self.user
        response = self.get_view()(
            request, dbgap_application_pk=self.dbgap_application.pk
        )
        self.assertTrue("form" in response.context_data)

    def test_form_class(self):
        """Form is the expected class."""
        request = self.factory.get(self.get_url(self.dbgap_application.pk))
        request.user = self.user
        response = self.get_view()(
            request, dbgap_application_pk=self.dbgap_application.pk
        )
        self.assertIsInstance(
            response.context_data["form"], forms.dbGaPDataAccessRequestFromJsonForm
        )

    @responses.activate
    def test_can_create_dars_from_json(self):
        """Can create dbGaPDataAccessRequests for this dbGaPApplication."""
        study_accession_1 = factories.dbGaPStudyAccessionFactory.create(phs=421)
        study_accession_2 = factories.dbGaPStudyAccessionFactory.create(phs=896)
        valid_json = [
            {
                "Project_id": self.dbgap_application.project_id,
                "PI_name": "Test Investigator",
                "Project_closed": "no",
                # Two studies.
                "studies": [
                    {
                        "study_name": "Test study 1",
                        "study_accession": "phs000421",
                        # N requests per study.
                        "requests": [
                            {
                                "DAC_abbrev": "FOOBI",
                                "consent_abbrev": "GRU",
                                "consent_code": 1,
                                "DAR": 23497,
                                "current_version": 12,
                                "current_DAR_status": "approved",
                                "was_approved": "yes",
                            },
                            {
                                "DAC_abbrev": "FOOBI",
                                "consent_abbrev": "HMB",
                                "consent_code": 2,
                                "DAR": 23498,
                                "current_version": 12,
                                "current_DAR_status": "approved",
                                "was_approved": "yes",
                            },
                        ],
                    },
                    {
                        "study_name": "Test study 2",
                        "study_accession": "phs000896",
                        # N requests per study.
                        "requests": [
                            {
                                "DAC_abbrev": "BARBI",
                                "consent_abbrev": "DS-LD",
                                "consent_code": 1,
                                "DAR": 23499,
                                "current_version": 12,
                                "current_DAR_status": "approved",
                                "was_approved": "yes",
                            },
                        ],
                    },
                ],
            }
        ]
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": "phs000421"})],
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs000421.v32.p18"
            },
        )
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": "phs000896"})],
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs000896.v2.p1"
            },
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.pk), {"json": json.dumps(valid_json)}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 3)
        # Make sure all the correct objects were created.
        # study 1, 2 requests.
        new_object = models.dbGaPDataAccessRequest.objects.get(dbgap_dar_id=23497)
        self.assertEqual(new_object.dbgap_application, self.dbgap_application)
        self.assertEqual(new_object.dbgap_study_accession, study_accession_1)
        self.assertEqual(new_object.dbgap_version, 32)
        self.assertEqual(new_object.dbgap_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        new_object = models.dbGaPDataAccessRequest.objects.get(dbgap_dar_id=23498)
        self.assertEqual(new_object.dbgap_application, self.dbgap_application)
        self.assertEqual(new_object.dbgap_study_accession, study_accession_1)
        self.assertEqual(new_object.dbgap_version, 32)
        self.assertEqual(new_object.dbgap_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 2)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "HMB")
        # study 2, one rquest
        new_object = models.dbGaPDataAccessRequest.objects.get(dbgap_dar_id=23499)
        self.assertEqual(new_object.dbgap_application, self.dbgap_application)
        self.assertEqual(new_object.dbgap_study_accession, study_accession_2)
        self.assertEqual(new_object.dbgap_version, 2)
        self.assertEqual(new_object.dbgap_participant_set, 1)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "DS-LD")

    @responses.activate
    def test_redirect_url(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.pk),
            {"json": json.dumps(self.valid_json)},
        )
        self.assertRedirects(response, self.dbgap_application.get_absolute_url())

    @responses.activate
    def test_success_message(self):
        """Redirects to successful url."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.pk),
            {"json": json.dumps(self.valid_json)},
            follow=True,
        )
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.dbGaPDataAccessRequestCreateFromJson.success_msg, str(messages[0])
        )

    def test_error_missing_json(self):
        """Form shows an error when study is missing."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.pk), {"json": ""}
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("required", form.errors["json"][0])

    def test_get_dbgap_application_pk_does_not_exist(self):
        """Raises a 404 error with an invalid object dbgap_application_pk."""
        request = self.factory.get(self.get_url(self.dbgap_application.pk + 1))
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, dbgap_application_pk=self.dbgap_application.pk + 1)

    def test_post_dbgap_application_pk_does_not_exist(self):
        """Raises a 404 error with an invalid object dbgap_application_pk."""
        request = self.factory.post(self.get_url(self.dbgap_application.pk + 1), {})
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(request, dbgap_application_pk=self.dbgap_application.pk + 1)

    def test_get_dars_already_added(self):
        """Redirects get request with a message when DARs have already been added for this application."""
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=self.dbgap_application
        )
        self.client.force_login(self.user)
        response = self.client.get(self.get_url(self.dbgap_application.pk), follow=True)
        self.assertRedirects(response, self.dbgap_application.get_absolute_url())
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.dbGaPDataAccessRequestCreateFromJson.ERROR_DARS_ALREADY_ADDED,
            str(messages[0]),
        )

    def test_post_dars_already_added(self):
        """Redirects post request with a message when DARs have already been added for this application."""
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=self.dbgap_application
        )
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.pk),
            {"json": json.dumps(self.valid_json)},
            follow=True,
        )
        self.assertRedirects(response, self.dbgap_application.get_absolute_url())
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.dbGaPDataAccessRequestCreateFromJson.ERROR_DARS_ALREADY_ADDED,
            str(messages[0]),
        )

    def test_post_invalid_json(self):
        """JSON is invalid."""
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.pk),
            {"json": json.dumps({"foo": "bar"})},
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("JSON validation error", form.errors["json"][0])

    def test_json_project_id_does_not_match(self):
        """Error message when project_id in JSON does not match project_id in dbGaPApplication."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(dbgap_application.pk), {"json": json.dumps(self.valid_json)}
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        # Form is valid...
        self.assertTrue(form.is_valid())
        # But there is an error.
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.dbGaPDataAccessRequestCreateFromJson.ERROR_PROJECT_ID_DOES_NOT_MATCH,
            str(messages[0]),
        )

    def test_json_phs_does_not_exist(self):
        """dbGaPStudyAccession with one of the phs's does not exist"""
        self.study_accession.delete()
        self.client.force_login(self.user)
        response = self.client.post(
            self.get_url(self.dbgap_application.pk),
            {"json": json.dumps(self.valid_json)},
        )
        self.assertEqual(response.status_code, 200)
        # No new objects were created.
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)
        # Form has errors in the correct field.
        self.assertIn("form", response.context_data)
        form = response.context_data["form"]
        # Form is valid...
        self.assertTrue(form.is_valid())
        # But there is an error.
        self.assertIn("messages", response.context)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            views.dbGaPDataAccessRequestCreateFromJson.ERROR_STUDY_ACCESSION_NOT_FOUND,
            str(messages[0]),
        )
