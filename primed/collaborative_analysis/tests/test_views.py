"""Tests for views related to the `collaborative_analysis` app."""

import responses
from anvil_consortium_manager.models import AnVILProjectManagerAccess, Workspace
from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    BillingProjectFactory,
    GroupAccountMembershipFactory,
    GroupGroupMembershipFactory,
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

from primed.cdsa.tests.factories import CDSAWorkspaceFactory
from primed.dbgap.tests.factories import dbGaPWorkspaceFactory
from primed.miscellaneous_workspaces.tests.factories import OpenAccessWorkspaceFactory
from primed.users.tests.factories import UserFactory

from .. import audit, models, views
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

    def test_link_to_audit_staff_view(self):
        """Links to the audit view page do appear on the detail page for staff viewers."""
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
        url = reverse(
            "collaborative_analysis:workspaces:audit",
            args=[obj.workspace.billing_project.name, obj.workspace.name],
        )
        self.assertIn(url, response.content.decode())

    def test_link_to_audit_view(self):
        """Links to the audit view page do not appear on the detail page for viewers."""
        obj = factories.CollaborativeAnalysisWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(obj.workspace.get_absolute_url())
        self.assertNotIn(
            reverse(
                "collaborative_analysis:workspaces:audit",
                args=[obj.workspace.billing_project.name, obj.workspace.name],
            ),
            response.content.decode(),
        )


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
        print(response.content)
        print(response.context_data["form"].errors)
        print(response.context_data["workspace_data_formset"].errors)
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


class WorkspaceAuditTest(TestCase):
    """Tests for the CollaborativeAnalysisWorkspaceAuditTest view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )
        self.collaborative_analysis_workspace = (
            factories.CollaborativeAnalysisWorkspaceFactory.create()
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "collaborative_analysis:workspaces:audit",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.WorkspaceAudit.as_view()

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
                self.collaborative_analysis_workspace.workspace.billing_project.name,
                self.collaborative_analysis_workspace.workspace.name,
            )
        )
        request.user = self.user
        response = self.get_view()(
            request,
            billing_project_slug=self.collaborative_analysis_workspace.workspace.billing_project.name,
            workspace_slug=self.collaborative_analysis_workspace.workspace.name,
        )
        self.assertEqual(response.status_code, 200)

    def test_access_without_user_permission(self):
        """Raises permission denied if user has no permissions."""
        user_no_perms = User.objects.create_user(
            username="test-none", password="test-none"
        )
        request = self.factory.get(
            self.get_url(
                self.collaborative_analysis_workspace.workspace.billing_project.name,
                self.collaborative_analysis_workspace.workspace.name,
            )
        )
        request.user = user_no_perms
        with self.assertRaises(PermissionDenied):
            self.get_view()(
                request,
                billing_project_slug=self.collaborative_analysis_workspace.workspace.billing_project.name,
                workspace_slug=self.collaborative_analysis_workspace.workspace.name,
            )

    def test_invalid_billing_project_name(self):
        """Raises a 404 error with an invalid object dbgap_application_pk."""
        request = self.factory.get(
            self.get_url("foo", self.collaborative_analysis_workspace.workspace.name)
        )
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(
                request,
                billing_project_slug="foo",
                workspace_slug=self.collaborative_analysis_workspace.workspace.name,
            )

    def test_invalid_workspace_name(self):
        """Raises a 404 error with an invalid object dbgap_application_pk."""
        request = self.factory.get(
            self.get_url(self.collaborative_analysis_workspace.workspace.name, "foo")
        )
        request.user = self.user
        with self.assertRaises(Http404):
            self.get_view()(
                request,
                billing_project_slug=self.collaborative_analysis_workspace.workspace.billing_project.name,
                workspace_slug="foo",
            )

    def test_context_data_access_audit(self):
        """The data_access_audit exists in the context."""
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.collaborative_analysis_workspace.workspace.billing_project.name,
                self.collaborative_analysis_workspace.workspace.name,
            )
        )
        self.assertIn("data_access_audit", response.context_data)
        self.assertIsInstance(
            response.context_data["data_access_audit"],
            audit.CollaborativeAnalysisWorkspaceAccessAudit,
        )
        self.assertTrue(response.context_data["data_access_audit"].completed)
        qs = response.context_data["data_access_audit"].queryset
        self.assertEqual(len(qs), 1)
        self.assertIn(self.collaborative_analysis_workspace, qs)

    def test_context_verified_table_access(self):
        """verified_table shows a record when audit has one account with verified access."""
        # Create accounts.
        account = AccountFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        self.collaborative_analysis_workspace.source_workspaces.add(
            source_workspace.workspace
        )
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=self.collaborative_analysis_workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace.workspace.authorization_domains.first(),
            account=account,
        )
        # CollaborativeAnalysisWorkspace auth domain membership.
        GroupAccountMembershipFactory.create(
            group=self.collaborative_analysis_workspace.workspace.authorization_domains.first(),
            account=account,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.collaborative_analysis_workspace.workspace.billing_project.name,
                self.collaborative_analysis_workspace.workspace.name,
            )
        )
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.AccessAuditResultsTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            self.collaborative_analysis_workspace,
        )
        self.assertEqual(table.rows[0].get_cell_value("member"), account)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.CollaborativeAnalysisWorkspaceAccessAudit.IN_SOURCE_AUTH_DOMAINS,
        )
        self.assertIsNone(table.rows[0].get_cell_value("action"))

    def test_context_verified_table_no_access(self):
        """verified_table shows a record when audit has one account with verified no access."""
        # Create accounts.
        account = AccountFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        self.collaborative_analysis_workspace.source_workspaces.add(
            source_workspace.workspace
        )
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=self.collaborative_analysis_workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace.workspace.authorization_domains.first(),
        #     account=account,
        # )
        # CollaborativeAnalysisWorkspace auth domain membership.
        # GroupAccountMembershipFactory.create(
        #     group=self.collaborative_analysis_workspace.workspace.authorization_domains.first(), account=account
        # )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.collaborative_analysis_workspace.workspace.billing_project.name,
                self.collaborative_analysis_workspace.workspace.name,
            )
        )
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.AccessAuditResultsTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            self.collaborative_analysis_workspace,
        )
        self.assertEqual(table.rows[0].get_cell_value("member"), account)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.CollaborativeAnalysisWorkspaceAccessAudit.NOT_IN_SOURCE_AUTH_DOMAINS,
        )
        self.assertIsNone(table.rows[0].get_cell_value("action"))

    def test_context_needs_action_table_grant(self):
        """needs_action_table shows a record when audit finds that access needs to be granted."""
        # Create accounts.
        account = AccountFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        self.collaborative_analysis_workspace.source_workspaces.add(
            source_workspace.workspace
        )
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=self.collaborative_analysis_workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace.workspace.authorization_domains.first(),
            account=account,
        )
        # CollaborativeAnalysisWorkspace auth domain membership.
        # GroupAccountMembershipFactory.create(
        #     group=self.collaborative_analysis_workspace.workspace.authorization_domains.first(), account=account
        # )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.collaborative_analysis_workspace.workspace.billing_project.name,
                self.collaborative_analysis_workspace.workspace.name,
            )
        )
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            audit.AccessAuditResultsTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            self.collaborative_analysis_workspace,
        )
        self.assertEqual(table.rows[0].get_cell_value("member"), account)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.CollaborativeAnalysisWorkspaceAccessAudit.IN_SOURCE_AUTH_DOMAINS,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_needs_action_table_remoe(self):
        """needs_action_table shows a record when audit finds that access needs to be removed."""
        # Create accounts.
        account = AccountFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        self.collaborative_analysis_workspace.source_workspaces.add(
            source_workspace.workspace
        )
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=self.collaborative_analysis_workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace.workspace.authorization_domains.first(),
        #     account=account,
        # )
        # CollaborativeAnalysisWorkspace auth domain membership.
        GroupAccountMembershipFactory.create(
            group=self.collaborative_analysis_workspace.workspace.authorization_domains.first(),
            account=account,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.collaborative_analysis_workspace.workspace.billing_project.name,
                self.collaborative_analysis_workspace.workspace.name,
            )
        )
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            audit.AccessAuditResultsTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            self.collaborative_analysis_workspace,
        )
        self.assertEqual(table.rows[0].get_cell_value("member"), account)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.CollaborativeAnalysisWorkspaceAccessAudit.NOT_IN_SOURCE_AUTH_DOMAINS,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_error_table_group_in_auth_domain(self):
        """error shows a record when audit finds a group in the auth domain."""
        # Create accounts.
        group = ManagedGroupFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=self.collaborative_analysis_workspace.workspace.authorization_domains.first(),
            child_group=group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(
            self.get_url(
                self.collaborative_analysis_workspace.workspace.billing_project.name,
                self.collaborative_analysis_workspace.workspace.name,
            )
        )
        self.assertIn("errors_table", response.context_data)
        table = response.context_data["errors_table"]
        self.assertIsInstance(
            table,
            audit.AccessAuditResultsTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            self.collaborative_analysis_workspace,
        )
        self.assertEqual(table.rows[0].get_cell_value("member"), group)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.CollaborativeAnalysisWorkspaceAccessAudit.UNEXPECTED_GROUP_ACCESS,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))


class WorkspaceAuditAllTest(TestCase):
    """Tests for the CollaborativeAnalysisWorkspaceAuditAllTest view."""

    def setUp(self):
        """Set up test class."""
        self.factory = RequestFactory()
        # Create a user with both view and edit permission.
        self.user = User.objects.create_user(username="test", password="test")
        self.user.user_permissions.add(
            Permission.objects.get(
                codename=AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME
            )
        )

    def get_url(self, *args):
        """Get the url for the view being tested."""
        return reverse(
            "collaborative_analysis:workspaces:audit_all",
            args=args,
        )

    def get_view(self):
        """Return the view being tested."""
        return views.WorkspaceAuditAll.as_view()

    def test_view_redirect_not_logged_in(self):
        "View redirects to login view when user is not logged in."
        # Need a client for redirects.
        response = self.client.get(self.get_url())
        self.assertRedirects(
            response,
            resolve_url(settings.LOGIN_URL) + "?next=" + self.get_url(),
        )

    def test_status_code_with_user_permission_view(self):
        """Returns successful response code if the user has view permission."""
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

    def test_context_data_access_audit_no_workspaces(self):
        """The data_access_audit exists in the context."""
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("data_access_audit", response.context_data)
        self.assertIsInstance(
            response.context_data["data_access_audit"],
            audit.CollaborativeAnalysisWorkspaceAccessAudit,
        )
        self.assertTrue(response.context_data["data_access_audit"].completed)
        qs = response.context_data["data_access_audit"].queryset
        self.assertEqual(len(qs), 0)

    def test_context_data_access_audit_one_workspace(self):
        """The data_access_audit exists in the context."""
        instance = factories.CollaborativeAnalysisWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("data_access_audit", response.context_data)
        self.assertIsInstance(
            response.context_data["data_access_audit"],
            audit.CollaborativeAnalysisWorkspaceAccessAudit,
        )
        self.assertTrue(response.context_data["data_access_audit"].completed)
        qs = response.context_data["data_access_audit"].queryset
        self.assertEqual(len(qs), 1)
        self.assertIn(instance, qs)

    def test_context_data_access_audit_two_workspaces(self):
        """The data_access_audit exists in the context."""
        instance_1 = factories.CollaborativeAnalysisWorkspaceFactory.create()
        instance_2 = factories.CollaborativeAnalysisWorkspaceFactory.create()
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("data_access_audit", response.context_data)
        self.assertIsInstance(
            response.context_data["data_access_audit"],
            audit.CollaborativeAnalysisWorkspaceAccessAudit,
        )
        self.assertTrue(response.context_data["data_access_audit"].completed)
        qs = response.context_data["data_access_audit"].queryset
        self.assertEqual(len(qs), 2)
        self.assertIn(instance_1, qs)
        self.assertIn(instance_2, qs)

    def test_context_verified_table_access(self):
        """verified_table shows a record when audit has one account with verified access."""
        instance = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Create accounts.
        account = AccountFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        instance.source_workspaces.add(source_workspace.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=instance.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace.workspace.authorization_domains.first(),
            account=account,
        )
        # CollaborativeAnalysisWorkspace auth domain membership.
        GroupAccountMembershipFactory.create(
            group=instance.workspace.authorization_domains.first(),
            account=account,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.AccessAuditResultsTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            instance,
        )
        self.assertEqual(table.rows[0].get_cell_value("member"), account)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.CollaborativeAnalysisWorkspaceAccessAudit.IN_SOURCE_AUTH_DOMAINS,
        )
        self.assertIsNone(table.rows[0].get_cell_value("action"))

    def test_context_verified_table_no_access(self):
        """verified_table shows a record when audit has one account with verified no access."""
        instance = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Create accounts.
        account = AccountFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        instance.source_workspaces.add(source_workspace.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=instance.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace.workspace.authorization_domains.first(),
        #     account=account,
        # )
        # CollaborativeAnalysisWorkspace auth domain membership.
        # GroupAccountMembershipFactory.create(
        #     group=instance.workspace.authorization_domains.first(), account=account
        # )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("verified_table", response.context_data)
        table = response.context_data["verified_table"]
        self.assertIsInstance(
            table,
            audit.AccessAuditResultsTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            instance,
        )
        self.assertEqual(table.rows[0].get_cell_value("member"), account)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.CollaborativeAnalysisWorkspaceAccessAudit.NOT_IN_SOURCE_AUTH_DOMAINS,
        )
        self.assertIsNone(table.rows[0].get_cell_value("action"))

    def test_context_needs_action_table_grant(self):
        """needs_action_table shows a record when audit finds that access needs to be granted."""
        instance = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Create accounts.
        account = AccountFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        instance.source_workspaces.add(source_workspace.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=instance.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace.workspace.authorization_domains.first(),
            account=account,
        )
        # CollaborativeAnalysisWorkspace auth domain membership.
        # GroupAccountMembershipFactory.create(
        #     group=self.collaborative_analysis_workspace.workspace.authorization_domains.first(), account=account
        # )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            audit.AccessAuditResultsTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            instance,
        )
        self.assertEqual(table.rows[0].get_cell_value("member"), account)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.CollaborativeAnalysisWorkspaceAccessAudit.IN_SOURCE_AUTH_DOMAINS,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_needs_action_table_remove(self):
        """needs_action_table shows a record when audit finds that access needs to be removed."""
        instance = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Create accounts.
        account = AccountFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        instance.source_workspaces.add(source_workspace.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=instance.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace.workspace.authorization_domains.first(),
        #     account=account,
        # )
        # CollaborativeAnalysisWorkspace auth domain membership.
        GroupAccountMembershipFactory.create(
            group=instance.workspace.authorization_domains.first(),
            account=account,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("needs_action_table", response.context_data)
        table = response.context_data["needs_action_table"]
        self.assertIsInstance(
            table,
            audit.AccessAuditResultsTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            instance,
        )
        self.assertEqual(table.rows[0].get_cell_value("member"), account)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.CollaborativeAnalysisWorkspaceAccessAudit.NOT_IN_SOURCE_AUTH_DOMAINS,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))

    def test_context_error_table_group_in_auth_domain(self):
        """error shows a record when audit finds a group in the auth domain."""
        instance = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Create accounts.
        group = ManagedGroupFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=instance.workspace.authorization_domains.first(),
            child_group=group,
        )
        # Check the table in the context.
        self.client.force_login(self.user)
        response = self.client.get(self.get_url())
        self.assertIn("errors_table", response.context_data)
        table = response.context_data["errors_table"]
        self.assertIsInstance(
            table,
            audit.AccessAuditResultsTable,
        )
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(
            table.rows[0].get_cell_value("workspace"),
            instance,
        )
        self.assertEqual(table.rows[0].get_cell_value("member"), group)
        self.assertEqual(
            table.rows[0].get_cell_value("note"),
            audit.CollaborativeAnalysisWorkspaceAccessAudit.UNEXPECTED_GROUP_ACCESS,
        )
        self.assertIsNotNone(table.rows[0].get_cell_value("action"))
