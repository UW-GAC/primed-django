"""Tests for views related to the `workspaces` app."""

import responses
from anvil_consortium_manager.models import AnVILProjectManagerAccess, Workspace, WorkspaceGroupSharing
from anvil_consortium_manager.tests.factories import (
    BillingProjectFactory,
    ManagedGroupFactory,
    WorkspaceFactory,
)
from anvil_consortium_manager.tests.utils import AnVILAPIMockTestMixin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from primed.primed_anvil.tests.factories import AvailableDataFactory, StudyFactory
from primed.users.tests.factories import UserFactory

from .. import models
from . import factories

User = get_user_model()


class SimulatedDataWorkspaceDetailTest(TestCase):
    """Tests of the WorkspaceDetail view from ACM with this app's SimulatedDataWorkspace model."""

    def setUp(self):
        """Set up test class."""
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        obj = factories.SimulatedDataWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertEqual(response.status_code, 200)


class SimulatedDataWorkspaceCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceCreate view from ACM with this app's SimulatedDataWorkspace model."""

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
        self.workspace_type = "simulated_data"
        self.admins_group = ManagedGroupFactory.create(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)

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
        # API response for PRIMED_ADMINS workspace owner.
        acls = [
            {
                "email": "TEST_PRIMED_CC_ADMINS@firecloud.org",
                "accessLevel": "OWNER",
                "canShare": False,
                "canCompute": True,
            }
        ]
        self.anvil_response_mock.add(
            responses.PATCH,
            self.api_client.rawls_entry_point
            + "/api/workspaces/test-billing-project/test-workspace/acl?inviteUsersNotFound=false",
            status=200,
            match=[responses.matchers.json_params_matcher(acls)],
            json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
        )
        # Make the post request
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
                "workspacedata-0-requested_by": self.requester.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.SimulatedDataWorkspace.objects.count(), 1)
        new_workspace_data = models.SimulatedDataWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        # Check that the workspace was shared with the admins group.
        sharing = WorkspaceGroupSharing.objects.get(workspace=new_workspace, group=self.admins_group)
        self.assertEqual(sharing.access, sharing.OWNER)


class SimulatedDataWorkspaceImportTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceImport view from ACM with this app's SimulatedDataWorkspace model."""

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
        self.workspace_type = "simulated_data"

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
                "workspacedata-0-requested_by": self.requester.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.SimulatedDataWorkspace.objects.count(), 1)
        new_workspace_data = models.SimulatedDataWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)


class ConsortiumDevelWorkspaceDetailTest(TestCase):
    """Tests of the WorkspaceDetail view from ACM with this app's ConsortiumDevelWorkspace model."""

    def setUp(self):
        """Set up test class."""
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        obj = factories.ConsortiumDevelWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertEqual(response.status_code, 200)


class ConsortiumDevelWorkspaceCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceCreate view from ACM with this app's ConsortiumDevelWorkspace model."""

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
        self.workspace_type = "devel"
        self.admins_group = ManagedGroupFactory.create(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)

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
        # API response for PRIMED_ADMINS workspace owner.
        acls = [
            {
                "email": "TEST_PRIMED_CC_ADMINS@firecloud.org",
                "accessLevel": "OWNER",
                "canShare": False,
                "canCompute": True,
            }
        ]
        self.anvil_response_mock.add(
            responses.PATCH,
            self.api_client.rawls_entry_point
            + "/api/workspaces/test-billing-project/test-workspace/acl?inviteUsersNotFound=false",
            status=200,
            match=[responses.matchers.json_params_matcher(acls)],
            json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
        )
        # Make the post request
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
                "workspacedata-0-requested_by": self.requester.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.ConsortiumDevelWorkspace.objects.count(), 1)
        new_workspace_data = models.ConsortiumDevelWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        # Check that the workspace was shared with the admins group.
        sharing = WorkspaceGroupSharing.objects.get(workspace=new_workspace, group=self.admins_group)
        self.assertEqual(sharing.access, sharing.OWNER)


class ConsortiumDevelWorkspaceImportTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceImport view from ACM with this app's ConsortiumDevelWorkspace model."""

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
        self.workspace_type = "devel"

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
                "workspacedata-0-requested_by": self.requester.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.ConsortiumDevelWorkspace.objects.count(), 1)
        new_workspace_data = models.ConsortiumDevelWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)


class ResourceWorkspaceDetailTest(TestCase):
    """Tests of the WorkspaceDetail view from ACM with this app's ResourceWorkspace model."""

    def setUp(self):
        """Set up test class."""
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        obj = factories.ResourceWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertEqual(response.status_code, 200)


class ResourceWorkspaceCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceCreate view from ACM with this app's ResourceWorkspace model."""

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
        self.workspace_type = "resource"
        self.admins_group = ManagedGroupFactory.create(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)

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
        # API response for PRIMED_ADMINS workspace owner.
        acls = [
            {
                "email": "TEST_PRIMED_CC_ADMINS@firecloud.org",
                "accessLevel": "OWNER",
                "canShare": False,
                "canCompute": True,
            }
        ]
        self.anvil_response_mock.add(
            responses.PATCH,
            self.api_client.rawls_entry_point
            + "/api/workspaces/test-billing-project/test-workspace/acl?inviteUsersNotFound=false",
            status=200,
            match=[responses.matchers.json_params_matcher(acls)],
            json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
        )
        # Make the post request
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
                "workspacedata-0-requested_by": self.requester.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.ResourceWorkspace.objects.count(), 1)
        new_workspace_data = models.ResourceWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        # Check that the workspace was shared with the admins group.
        sharing = WorkspaceGroupSharing.objects.get(workspace=new_workspace, group=self.admins_group)
        self.assertEqual(sharing.access, sharing.OWNER)


class ResourceWorkspaceImportTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceImport view from ACM with this app's ResourceWorkspace model."""

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
        self.workspace_type = "resource"

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
                "workspacedata-0-requested_by": self.requester.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.ResourceWorkspace.objects.count(), 1)
        new_workspace_data = models.ResourceWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)


class TemplateWorkspaceDetailTest(TestCase):
    """Tests of the WorkspaceDetail view from ACM with this app's TemplateWorkspace model."""

    def setUp(self):
        """Set up test class."""
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        obj = factories.TemplateWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertEqual(response.status_code, 200)


class TemplateWorkspaceCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceCreate view from ACM with this app's TemplateWorkspace model."""

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
        self.workspace_type = "template"
        self.admins_group = ManagedGroupFactory.create(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)

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
        # API response for PRIMED_ADMINS workspace owner.
        acls = [
            {
                "email": "TEST_PRIMED_CC_ADMINS@firecloud.org",
                "accessLevel": "OWNER",
                "canShare": False,
                "canCompute": True,
            }
        ]
        self.anvil_response_mock.add(
            responses.PATCH,
            self.api_client.rawls_entry_point
            + "/api/workspaces/test-billing-project/test-workspace/acl?inviteUsersNotFound=false",
            status=200,
            match=[responses.matchers.json_params_matcher(acls)],
            json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
        )
        # Make the post request
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
                "workspacedata-0-intended_usage": "Test usage",
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.TemplateWorkspace.objects.count(), 1)
        new_workspace_data = models.TemplateWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(new_workspace_data.intended_usage, "Test usage")
        # Check that the workspace was shared with the admins group.
        sharing = WorkspaceGroupSharing.objects.get(workspace=new_workspace, group=self.admins_group)
        self.assertEqual(sharing.access, sharing.OWNER)


class TemplateWorkspaceImportTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceImport view from ACM with this app's TemplateWorkspace model."""

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
        self.workspace_type = "template"

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
                "workspacedata-0-intended_usage": "Test usage",
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.TemplateWorkspace.objects.count(), 1)
        new_workspace_data = models.TemplateWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(new_workspace_data.intended_usage, "Test usage")


class OpenAccessWorkspaceDetailTest(TestCase):
    """Tests of the WorkspaceDetail view from ACM with this app's OpenAccessWorkspace model."""

    def setUp(self):
        """Set up test class."""
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        obj = factories.OpenAccessWorkspaceFactory.create()
        study = StudyFactory.create()
        obj.studies.add(study)
        available_data = AvailableDataFactory.create()
        obj.available_data.add(available_data)
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertEqual(response.status_code, 200)


class OpenAccessWorkspaceCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceCreate view from ACM with this app's OpenAccessWorkspace model."""

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
        self.workspace_type = "open_access"
        self.requester = UserFactory.create()
        self.study = StudyFactory.create()
        self.admins_group = ManagedGroupFactory.create(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)

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
        # API response for PRIMED_ADMINS workspace owner.
        acls = [
            {
                "email": "TEST_PRIMED_CC_ADMINS@firecloud.org",
                "accessLevel": "OWNER",
                "canShare": False,
                "canCompute": True,
            }
        ]
        self.anvil_response_mock.add(
            responses.PATCH,
            self.api_client.rawls_entry_point
            + "/api/workspaces/test-billing-project/test-workspace/acl?inviteUsersNotFound=false",
            status=200,
            match=[responses.matchers.json_params_matcher(acls)],
            json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
        )
        # Make the post request
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
                "workspacedata-0-studies": [self.study.pk],
                "workspacedata-0-requested_by": self.requester.pk,
                "workspacedata-0-data_source": "test source",
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.OpenAccessWorkspace.objects.count(), 1)
        new_workspace_data = models.OpenAccessWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(new_workspace_data.requested_by, self.requester)
        self.assertEqual(new_workspace_data.studies.count(), 1)
        self.assertIn(self.study, new_workspace_data.studies.all())
        self.assertEqual(new_workspace_data.data_source, "test source")
        # Check that the workspace was shared with the admins group.
        sharing = WorkspaceGroupSharing.objects.get(workspace=new_workspace, group=self.admins_group)
        self.assertEqual(sharing.access, sharing.OWNER)


class OpenAccessWorkspaceImportTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceImport view from ACM with this app's OpenAccessWorkspace model."""

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
        self.workspace_type = "open_access"
        self.requester = UserFactory.create()
        self.study = StudyFactory.create()

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
                "workspacedata-0-studies": [self.study.pk],
                "workspacedata-0-requested_by": self.requester.pk,
                "workspacedata-0-data_source": "test source",
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.OpenAccessWorkspace.objects.count(), 1)
        new_workspace_data = models.OpenAccessWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        self.assertEqual(new_workspace_data.requested_by, self.requester)
        self.assertEqual(new_workspace_data.studies.count(), 1)
        self.assertIn(self.study, new_workspace_data.studies.all())
        self.assertEqual(new_workspace_data.data_source, "test source")


class DataPrepWorkspaceDetailTest(TestCase):
    """Tests of the WorkspaceDetail view from ACM with this app's DataPrepWorkspace model."""

    def setUp(self):
        """Set up test class."""
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME)
        )

    def test_status_code_with_user_permission(self):
        """Returns successful response code."""
        obj = factories.DataPrepWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        # Includes link to target workspace.
        self.assertContains(response, obj.target_workspace.get_absolute_url())

    def test_template_active(self):
        """Returns successful response code."""
        obj = factories.DataPrepWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active")

    def test_template_inactive(self):
        """Returns successful response code."""
        obj = factories.DataPrepWorkspaceFactory.create(is_active=False)
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inactive")


class DataPrepWorkspaceCreateTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceCreate view from ACM with this app's DataPrepWorkspace model."""

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
        self.target_workspace = WorkspaceFactory.create()
        self.workspace_type = "data_prep"
        self.admins_group = ManagedGroupFactory.create(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)

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
        # API response for PRIMED_ADMINS workspace owner.
        acls = [
            {
                "email": "TEST_PRIMED_CC_ADMINS@firecloud.org",
                "accessLevel": "OWNER",
                "canShare": False,
                "canCompute": True,
            }
        ]
        self.anvil_response_mock.add(
            responses.PATCH,
            self.api_client.rawls_entry_point
            + "/api/workspaces/test-billing-project/test-workspace/acl?inviteUsersNotFound=false",
            status=200,
            match=[responses.matchers.json_params_matcher(acls)],
            json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
        )
        # Make the post request
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
                "workspacedata-0-target_workspace": self.target_workspace.pk,
                "workspacedata-0-requested_by": self.requester.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.DataPrepWorkspace.objects.count(), 1)
        new_workspace_data = models.DataPrepWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
        # Check that the workspace was shared with the admins group.
        sharing = WorkspaceGroupSharing.objects.get(workspace=new_workspace, group=self.admins_group)
        self.assertEqual(sharing.access, sharing.OWNER)


class DataPrepWorkspaceImportTest(AnVILAPIMockTestMixin, TestCase):
    """Tests of the WorkspaceImport view from ACM with this app's DataPrepWorkspace model."""

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
        self.target_workspace = WorkspaceFactory.create()
        self.workspace_type = "data_prep"

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
                "workspacedata-0-target_workspace": self.target_workspace.pk,
                "workspacedata-0-requested_by": self.requester.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        # The workspace is created.
        new_workspace = Workspace.objects.latest("pk")
        # Workspace data is added.
        self.assertEqual(models.DataPrepWorkspace.objects.count(), 1)
        new_workspace_data = models.DataPrepWorkspace.objects.latest("pk")
        self.assertEqual(new_workspace_data.workspace, new_workspace)
