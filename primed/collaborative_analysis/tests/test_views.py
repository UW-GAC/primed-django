"""Tests for views related to the `collaborative_analysis` app."""

import responses
from anvil_consortium_manager.models import AnVILProjectManagerAccess, Workspace
from anvil_consortium_manager.tests.factories import (
    BillingProjectFactory,
    ManagedGroupFactory,
)
from anvil_consortium_manager.tests.utils import AnVILAPIMockTestMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from primed.cdsa.tests.factories import CDSAWorkspaceFactory
from primed.dbgap.tests.factories import dbGaPWorkspaceFactory
from primed.miscellaneous_workspaces.tests.factories import OpenAccessWorkspaceFactory
from primed.users.tests.factories import UserFactory

from .. import models
from . import factories

User = get_user_model()


class CollaborativeAnalysisWorkspaceDetailTest(TestCase):
    """Tests of the WorkspaceDetail view from ACM with this app's CollaborativeAnalysisWorkspace model."""

    def setUp(self):
        """Set up test class."""
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.VIEW_PERMISSION_CODENAME
            )
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        obj = factories.CollaborativeAnalysisWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_links_to_source_workspace(self):
        """Links to the source workspace appear on the detail page."""
        # TODO: Move this to a table in the context data when ACM allows.
        obj = factories.CollaborativeAnalysisWorkspaceFactory.create()
        dbgap_workspace = dbGaPWorkspaceFactory.create()
        cdsa_workspace = CDSAWorkspaceFactory.create()
        open_access_workspace = OpenAccessWorkspaceFactory.create()
        obj.source_workspaces.add(
            dbgap_workspace.workspace,
            cdsa_workspace.workspace,
            open_access_workspace.workspace,
        )
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertIn(dbgap_workspace.get_absolute_url(), response.content.decode())
        self.assertIn(cdsa_workspace.get_absolute_url(), response.content.decode())
        self.assertIn(
            open_access_workspace.get_absolute_url(), response.content.decode()
        )

    def test_link_to_custodian(self):
        """Links to the custodian's user profile appear on the detail page."""
        custodian = UserFactory.create()
        obj = factories.CollaborativeAnalysisWorkspaceFactory.create(
            custodian=custodian
        )
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertIn(custodian.get_absolute_url(), response.content.decode())

    def test_link_to_analyst_group_staff_view(self):
        """Links to the analyst group's detail page appear on the detail page for staff_viewers."""
        user = User.objects.create_user(
            username="test-staff-view", password="test-staff-view"
        )
        user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        obj = factories.CollaborativeAnalysisWorkspaceFactory.create()
        self.client.force_login(user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertIn(obj.analyst_group.get_absolute_url(), response.content.decode())
        self.assertIn(obj.analyst_group.name, response.content.decode())

    def test_link_to_analyst_group_view(self):
        """Links to the analyst group's detail page do not appear on the detail page for viewers."""
        obj = factories.CollaborativeAnalysisWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertNotIn(
            obj.analyst_group.get_absolute_url(), response.content.decode()
        )
        self.assertNotIn(obj.analyst_group.name, response.content.decode())


class CollaborativeAnalysisWorkspaceCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceCreate view from ACM with this app's CollaborativeAnalysisWorkspace model."""

    api_success_code = 201

    def setUp(self):
        """Set up test class."""
        # The superclass uses the responses package to mock API responses.
        super().setUp()
        # Create a user with both view and edit permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        self.workspace_type = "collab_analysis"
        self.custodian = UserFactory.create()
        self.source_workspace = dbGaPWorkspaceFactory.create()
        self.analyst_group = ManagedGroupFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:workspaces:new", args=args)

    def test_creates_workspace(self):
        """Posting valid data to the form creates a workspace data object when using a custom adapter."""
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
                "workspacedata-0-custodian": self.custodian.pk,
                "workspacedata-0-source_workspaces": [self.source_workspace.pk],
                "workspacedata-0-purpose": "test",
                "workspacedata-0-analyst_group": self.analyst_group.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.CollaborativeAnalysisWorkspace.objects.count(), 1)
        new_workspace_data = models.CollaborativeAnalysisWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)


class CollaborativeAnalysisWorkspaceImportTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceImport view from ACM with this app's CollaborativeAnalysisWorkspace model."""

    api_success_code = 200

    def setUp(self):
        """Set up test class."""
        # The superclass uses the responses package to mock API responses.
        super().setUp()
        # Create a user with both view and edit permissions.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
            )
        )
        self.custodian = UserFactory.create()
        self.source_workspace = dbGaPWorkspaceFactory.create()
        self.workspace_type = "collab_analysis"
        self.analyst_group = ManagedGroupFactory.create()

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse("anvil_consortium_manager:workspaces:import", args=args)

    def get_api_url(self, billing_project_name, workspace_name):
        """Return the Terra API url for a given billing project and workspace."""
        return (
            self.api_client.rawls_entry_point
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
                "isLocked": False,
            },
        }
        return json_data

    def test_creates_workspace(self):
        """Posting valid data to the form creates an UploadWorkspace object."""
        billing_project = BillingProjectFactory.create(name="billing-project")
        workspace_name = "workspace"
        # Available workspaces API call.
        workspace_list_url = self.api_client.rawls_entry_point + "/api/workspaces"
        self.anvil_response_mock.add(
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
                "workspacedata-0-custodian": self.custodian.pk,
                "workspacedata-0-source_workspaces": [self.source_workspace.pk],
                "workspacedata-0-purpose": "test",
                "workspacedata-0-analyst_group": self.analyst_group.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.CollaborativeAnalysisWorkspace.objects.count(), 1)
        new_workspace_data = models.CollaborativeAnalysisWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
