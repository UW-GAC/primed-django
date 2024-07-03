import responses
from anvil_consortium_manager.models import (
    GroupGroupMembership,
    WorkspaceGroupSharing,
)
from anvil_consortium_manager.tests.factories import (
    ManagedGroupFactory,
    WorkspaceFactory,
)
from anvil_consortium_manager.tests.utils import AnVILAPIMockTestMixin
from django.conf import settings
from django.test import TestCase, override_settings

from .. import adapters
from . import factories


class CollaborativeAnalysisWorkspaceAdapterTest(AnVILAPIMockTestMixin, TestCase):
    """Tests for methods in the CollaborativeAnalysisWorkspaceAdapter."""

    def setUp(self):
        super().setUp()
        self.adapter = adapters.CollaborativeAnalysisWorkspaceAdapter()
        # Create the admins group.
        self.admins_group = ManagedGroupFactory.create(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)

    def test_before_anvil_create(self):
        # Create a Workspace instead of CDSAWorkspace to skip factory auth domain behavior.
        workspace = WorkspaceFactory.create(name="foo", workspace_type=self.adapter.get_type())
        # API response for auth domain ManagedGroup creation.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point + "/api/groups/v1/AUTH_foo",
            status=201,
        )
        # API response for auth domain PRIMED_ADMINS membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + "/api/groups/v1/AUTH_foo/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        # Run the adapter method.
        self.adapter.before_anvil_create(workspace)
        self.assertEqual(workspace.authorization_domains.count(), 1)
        auth_domain = workspace.authorization_domains.first()
        self.assertEqual(auth_domain.name, "AUTH_foo")
        self.assertTrue(auth_domain.is_managed_by_app)
        self.assertEqual(auth_domain.email, "AUTH_foo@firecloud.org")
        # Check for GroupGroupMembership.
        self.assertEqual(GroupGroupMembership.objects.count(), 1)
        membership = GroupGroupMembership.objects.first()
        self.assertEqual(membership.parent_group, auth_domain)
        self.assertEqual(membership.child_group, self.admins_group)

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="foobar")
    def test_before_anvil_create_different_cc_admins_name(self):
        admins_group = ManagedGroupFactory.create(name="foobar")
        # Create a Workspace instead of CDSAWorkspace to skip factory auth domain behavior.
        workspace = WorkspaceFactory.create(name="foo", workspace_type=self.adapter.get_type())
        # API response for auth domain ManagedGroup creation.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point + "/api/groups/v1/AUTH_foo",
            status=201,
        )
        # API response for auth domain PRIMED_ADMINS membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + "/api/groups/v1/AUTH_foo/admin/foobar@firecloud.org",
            status=204,
        )
        # Run the adapter method.
        self.adapter.before_anvil_create(workspace)
        self.assertEqual(workspace.authorization_domains.count(), 1)
        auth_domain = workspace.authorization_domains.first()
        self.assertEqual(auth_domain.name, "AUTH_foo")
        self.assertTrue(auth_domain.is_managed_by_app)
        self.assertEqual(auth_domain.email, "AUTH_foo@firecloud.org")
        # Check for GroupGroupMembership.
        self.assertEqual(GroupGroupMembership.objects.count(), 1)
        membership = GroupGroupMembership.objects.first()
        self.assertEqual(membership.parent_group, auth_domain)
        self.assertEqual(membership.child_group, admins_group)

    def test_after_anvil_create(self):
        # Create a Workspace instead of CDSAWorkspace to skip factory auth domain behavior.
        collab_workspace = factories.CollaborativeAnalysisWorkspaceFactory.create(
            workspace__billing_project__name="bar", workspace__name="foo"
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
            self.api_client.rawls_entry_point + "/api/workspaces/bar/foo/acl?inviteUsersNotFound=false",
            status=200,
            match=[responses.matchers.json_params_matcher(acls)],
            json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
        )
        # Run the adapter method.
        self.adapter.after_anvil_create(collab_workspace.workspace)
        # Check for WorkspaceGroupSharing.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
        sharing = WorkspaceGroupSharing.objects.first()
        self.assertEqual(sharing.workspace, collab_workspace.workspace)
        self.assertEqual(sharing.group, self.admins_group)
        self.assertEqual(sharing.access, WorkspaceGroupSharing.OWNER)
        self.assertTrue(sharing.can_compute)

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="foobar")
    def test_after_anvil_create_different_admins_group(self):
        admins_group = ManagedGroupFactory.create(name="foobar")
        collab_workspace = factories.CollaborativeAnalysisWorkspaceFactory.create(
            workspace__billing_project__name="bar", workspace__name="foo"
        )
        # API response for PRIMED_ADMINS workspace owner.
        acls = [
            {
                "email": "foobar@firecloud.org",
                "accessLevel": "OWNER",
                "canShare": False,
                "canCompute": True,
            }
        ]
        self.anvil_response_mock.add(
            responses.PATCH,
            self.api_client.rawls_entry_point + "/api/workspaces/bar/foo/acl?inviteUsersNotFound=false",
            status=200,
            match=[responses.matchers.json_params_matcher(acls)],
            json={"invitesSent": {}, "usersNotFound": {}, "usersUpdated": acls},
        )
        # Run the adapter method.
        self.adapter.after_anvil_create(collab_workspace.workspace)
        # Check for WorkspaceGroupSharing.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
        sharing = WorkspaceGroupSharing.objects.first()
        self.assertEqual(sharing.workspace, collab_workspace.workspace)
        self.assertEqual(sharing.group, admins_group)
        self.assertEqual(sharing.access, WorkspaceGroupSharing.OWNER)
        self.assertTrue(sharing.can_compute)
