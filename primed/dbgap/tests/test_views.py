"""Tests for views related to the `dbgap` app."""

import responses
from anvil_consortium_manager import models as acm_models
from anvil_consortium_manager import views as acm_views
from anvil_consortium_manager.tests import factories as acm_factories
from anvil_consortium_manager.tests.utils import AnVILAPIMockTestMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.urls import reverse

from primed.primed_anvil.tests.factories import (
    DataUseModifierFactory,
    DataUsePermissionFactory,
)

from .. import models, tables
from . import factories

User = get_user_model()


class dbGaPWorkspaceListTest(TestCase):
    """Tests of the anvil_consortium_manager WorkspaceList view using this app's dbGaPWorkspaceAdapter."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
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
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
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
        dbgap_study = factories.dbGaPStudyFactory.create()
        data_use_permission = DataUsePermissionFactory.create()
        data_use_modifier_1 = DataUseModifierFactory.create()
        data_use_modifier_2 = DataUseModifierFactory.create()
        # Create an extra that won't be specified.
        DataUseModifierFactory.create()
        billing_project = acm_factories.BillingProjectFactory.create(
            name="test-billing-project"
        )
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
                "workspacedata-0-dbgap_study": dbgap_study.pk,
                "workspacedata-0-dbgap_version": 2,
                "workspacedata-0-dbgap_participant_set": 3,
                "workspacedata-0-full_consent_code": "GRU-TEST",
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
        new_workspace = acm_models.Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.dbGaPWorkspace.objects.count(), 1)
        new_workspace_data = models.dbGaPWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(new_workspace_data.dbgap_study, dbgap_study)
        self.assertEqual(new_workspace_data.dbgap_version, 2)
        self.assertEqual(new_workspace_data.dbgap_participant_set, 3)
        self.assertEqual(new_workspace_data.full_consent_code, "GRU-TEST")
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
                codename=acm_models.AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=acm_models.AnVILProjectManagerAccess.EDIT_PERMISSION_CODENAME
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
        dbgap_study = factories.dbGaPStudyFactory.create()
        data_use_permission = DataUsePermissionFactory.create()
        data_use_modifier_1 = DataUseModifierFactory.create()
        data_use_modifier_2 = DataUseModifierFactory.create()
        # Create an extra that won't be specified.
        DataUseModifierFactory.create()
        billing_project = acm_factories.BillingProjectFactory.create(
            name="billing-project"
        )
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
                "workspacedata-0-dbgap_study": dbgap_study.pk,
                "workspacedata-0-dbgap_version": 2,
                "workspacedata-0-dbgap_participant_set": 3,
                "workspacedata-0-full_consent_code": "GRU-TEST",
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
        new_workspace = acm_models.Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.dbGaPWorkspace.objects.count(), 1)
        new_workspace_data = models.dbGaPWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(new_workspace_data.dbgap_study, dbgap_study)
        self.assertEqual(new_workspace_data.dbgap_version, 2)
        self.assertEqual(new_workspace_data.dbgap_participant_set, 3)
        self.assertEqual(new_workspace_data.full_consent_code, "GRU-TEST")
        self.assertEqual(new_workspace_data.data_use_limitations, "test limitations")
        self.assertEqual(new_workspace_data.data_use_permission, data_use_permission)
        self.assertEqual(new_workspace_data.data_use_modifiers.count(), 2)
        self.assertIn(data_use_modifier_1, new_workspace_data.data_use_modifiers.all())
        self.assertIn(data_use_modifier_2, new_workspace_data.data_use_modifiers.all())
        responses.assert_call_count(url, 1)
