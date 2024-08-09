import responses
from anvil_consortium_manager.adapters.default import DefaultWorkspaceAdapter
from anvil_consortium_manager.models import Account, GroupGroupMembership, WorkspaceGroupSharing
from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    ManagedGroupFactory,
    WorkspaceFactory,
    WorkspaceGroupSharingFactory,
)
from anvil_consortium_manager.tests.utils import AnVILAPIMockTestMixin
from django.test import TestCase, override_settings

from primed.users.tests.factories import UserFactory

from .. import adapters


class AccountAdapterTest(TestCase):
    """Tests of the AccountAdapter, where not tested in other TestCases."""

    def test_get_autocomplete_label_linked_user(self):
        """get_autcomplete_label returns correct string when account has a linked user."""
        user = UserFactory.create(name="Test name")
        account = AccountFactory.create(email="foo@bar.com", user=user, verified=True)
        self.assertEqual(
            adapters.AccountAdapter().get_autocomplete_label(account),
            "Test name (foo@bar.com)",
        )

    def test_get_autocomplete_label_no_linked_user(self):
        """get_autcomplete_label returns correct string when account does not have a linked user."""
        account = AccountFactory.create(email="foo@bar.com")
        self.assertEqual(
            adapters.AccountAdapter().get_autocomplete_label(account),
            "--- (foo@bar.com)",
        )

    def test_autocomplete_queryset_matches_user_name(self):
        """get_autocomplete_label returns correct account when user name matches."""
        user_1 = UserFactory.create(name="First Last")
        account_1 = AccountFactory.create(email="test1@test.com", user=user_1, verified=True)
        user_2 = UserFactory.create(name="Foo Bar")
        account_2 = AccountFactory.create(email="test2@test.com", user=user_2, verified=True)
        queryset = adapters.AccountAdapter().get_autocomplete_queryset(Account.objects.all(), "last")
        self.assertEqual(len(queryset), 1)
        self.assertIn(account_1, queryset)
        self.assertNotIn(account_2, queryset)

    def test_autocomplete_queryset_matches_account_email(self):
        """get_autocomplete_label returns correct account when user email matches."""
        user_1 = UserFactory.create(name="First Last")
        account_1 = AccountFactory.create(email="test1@test.com", user=user_1, verified=True)
        user_2 = UserFactory.create(name="Foo Bar")
        account_2 = AccountFactory.create(email="username@domain.com", user=user_2, verified=True)
        queryset = adapters.AccountAdapter().get_autocomplete_queryset(Account.objects.all(), "test")
        self.assertEqual(len(queryset), 1)
        self.assertIn(account_1, queryset)
        self.assertNotIn(account_2, queryset)

    def test_autocomplete_queryset_no_linked_user(self):
        """get_autocomplete_label returns correct account when user name matches."""
        account_1 = AccountFactory.create(email="foo@bar.com")
        account_2 = AccountFactory.create(email="test@test.com")
        queryset = adapters.AccountAdapter().get_autocomplete_queryset(Account.objects.all(), "bar")
        self.assertEqual(len(queryset), 1)
        self.assertIn(account_1, queryset)
        self.assertNotIn(account_2, queryset)


class WorkspaceAuthDomainAdapterMixinTest(AnVILAPIMockTestMixin, TestCase):
    def setUp(self):
        super().setUp()

        class TestAdapter(adapters.WorkspaceAuthDomainAdapterMixin, DefaultWorkspaceAdapter):
            pass

        self.adapter = TestAdapter()

    def test_before_anvil_create(self):
        admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")
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
        self.assertEqual(membership.child_group, admins_group)

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

    def test_before_anvil_create_admins_group_does_not_exist(self):
        """If the admins group does not exist, the workspace is not shared."""
        workspace = WorkspaceFactory.create(name="foo", workspace_type=self.adapter.get_type())
        # API response for auth domain ManagedGroup creation.
        self.anvil_response_mock.add(
            responses.POST,
            self.api_client.sam_entry_point + "/api/groups/v1/AUTH_foo",
            status=201,
        )
        # Run the adapter method.
        self.adapter.before_anvil_create(workspace)
        self.assertEqual(workspace.authorization_domains.count(), 1)
        auth_domain = workspace.authorization_domains.first()
        self.assertEqual(auth_domain.name, "AUTH_foo")
        self.assertTrue(auth_domain.is_managed_by_app)
        self.assertEqual(auth_domain.email, "AUTH_foo@firecloud.org")
        # No GroupGroupMembership objects were created.
        self.assertEqual(GroupGroupMembership.objects.count(), 0)


class WorkspaceAdminSharingAdapterMixin(AnVILAPIMockTestMixin, TestCase):
    def setUp(self):
        super().setUp()

        class TestAdapter(adapters.WorkspaceAdminSharingAdapterMixin, DefaultWorkspaceAdapter):
            pass

        self.adapter = TestAdapter()

    def test_after_anvil_create(self):
        admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")
        workspace = WorkspaceFactory.create(
            billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
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
        self.adapter.after_anvil_create(workspace)
        # Check for WorkspaceGroupSharing.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
        sharing = WorkspaceGroupSharing.objects.first()
        self.assertEqual(sharing.workspace, workspace)
        self.assertEqual(sharing.group, admins_group)
        self.assertEqual(sharing.access, WorkspaceGroupSharing.OWNER)
        self.assertTrue(sharing.can_compute)

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="foobar")
    def test_after_anvil_create_different_admins_group(self):
        admins_group = ManagedGroupFactory.create(name="foobar")
        workspace = WorkspaceFactory.create(
            billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
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
        self.adapter.after_anvil_create(workspace)
        # Check for WorkspaceGroupSharing.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
        sharing = WorkspaceGroupSharing.objects.first()
        self.assertEqual(sharing.workspace, workspace)
        self.assertEqual(sharing.group, admins_group)
        self.assertEqual(sharing.access, WorkspaceGroupSharing.OWNER)
        self.assertTrue(sharing.can_compute)

    def test_after_anvil_create_no_admins_group(self):
        workspace = WorkspaceFactory.create(
            billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
        )
        # Run the adapter method.
        self.adapter.after_anvil_create(workspace)
        # No WorkspaceGroupSharing objects were created.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 0)

    def test_after_anvil_import(self):
        admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")
        workspace = WorkspaceFactory.create(
            billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
        )
        # API response for admin group workspace owner.
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
        self.adapter.after_anvil_import(workspace)
        # Check for WorkspaceGroupSharing.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
        sharing = WorkspaceGroupSharing.objects.first()
        self.assertEqual(sharing.workspace, workspace)
        self.assertEqual(sharing.group, admins_group)
        self.assertEqual(sharing.access, WorkspaceGroupSharing.OWNER)
        self.assertTrue(sharing.can_compute)

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="foobar")
    def test_after_anvil_import_different_admins_group(self):
        admins_group = ManagedGroupFactory.create(name="foobar")
        workspace = WorkspaceFactory.create(
            billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
        )
        # API response for admin group workspace owner.
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
        self.adapter.after_anvil_import(workspace)
        # Check for WorkspaceGroupSharing.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
        sharing = WorkspaceGroupSharing.objects.first()
        self.assertEqual(sharing.workspace, workspace)
        self.assertEqual(sharing.group, admins_group)
        self.assertEqual(sharing.access, WorkspaceGroupSharing.OWNER)
        self.assertTrue(sharing.can_compute)

    def test_after_anvil_import_no_admins_group(self):
        workspace = WorkspaceFactory.create(
            billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
        )
        # Run the adapter method.
        self.adapter.after_anvil_import(workspace)
        # No WorkspaceGroupSharing objects were created.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 0)

    def test_after_anvil_import_already_shared(self):
        admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")
        workspace = WorkspaceFactory.create(workspace_type=self.adapter.get_type())
        WorkspaceGroupSharingFactory.create(
            workspace=workspace,
            group=admins_group,
            access=WorkspaceGroupSharing.OWNER,
            can_compute=True,
        )
        # No API call - record already exists.
        # Run the adapter method.
        self.adapter.after_anvil_import(workspace)
        # Check for WorkspaceGroupSharing.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
        sharing = WorkspaceGroupSharing.objects.first()
        self.assertEqual(sharing.workspace, workspace)
        self.assertEqual(sharing.group, admins_group)
        self.assertEqual(sharing.access, WorkspaceGroupSharing.OWNER)
        self.assertTrue(sharing.can_compute)

    def test_after_anvil_import_already_shared_wrong_access(self):
        admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")
        workspace = WorkspaceFactory.create(
            billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
        )
        sharing = WorkspaceGroupSharingFactory.create(
            workspace=workspace,
            group=admins_group,
            access=WorkspaceGroupSharing.READER,
            can_compute=True,
        )
        # API response to update sharing.
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
        self.adapter.after_anvil_import(workspace)
        # Check for WorkspaceGroupSharing.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
        sharing.refresh_from_db()
        self.assertEqual(sharing.workspace, workspace)
        self.assertEqual(sharing.group, admins_group)
        self.assertEqual(sharing.access, WorkspaceGroupSharing.OWNER)
        self.assertTrue(sharing.can_compute)

    def test_after_anvil_import_already_shared_wrong_can_compute(self):
        admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")
        workspace = WorkspaceFactory.create(
            billing_project__name="bar", name="foo", workspace_type=self.adapter.get_type()
        )
        sharing = WorkspaceGroupSharingFactory.create(
            workspace=workspace,
            group=admins_group,
            access=WorkspaceGroupSharing.OWNER,
            can_compute=False,
        )
        # API response to update sharing.
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
        self.adapter.after_anvil_import(workspace)
        # Check for WorkspaceGroupSharing.
        self.assertEqual(WorkspaceGroupSharing.objects.count(), 1)
        sharing.refresh_from_db()
        self.assertEqual(sharing.workspace, workspace)
        self.assertEqual(sharing.group, admins_group)
        self.assertEqual(sharing.access, WorkspaceGroupSharing.OWNER)
        self.assertTrue(sharing.can_compute)


class ManagedGroupAdapterTest(AnVILAPIMockTestMixin, TestCase):
    """Tests for the custom PRIMED ManagedGroupAdapter."""

    def setUp(self):
        super().setUp()
        self.adapter = adapters.ManagedGroupAdapter()

    def test_after_anvil_create(self):
        admins_group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")
        managed_group = ManagedGroupFactory.create(name="test-group")
        # API response for PRIMED_ADMINS membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + "/api/groups/v1/test-group/admin/TEST_PRIMED_CC_ADMINS@firecloud.org",
            status=204,
        )
        # Run the adapter method.
        self.adapter.after_anvil_create(managed_group)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupGroupMembership.objects.count(), 1)
        membership = GroupGroupMembership.objects.first()
        self.assertEqual(membership.parent_group, managed_group)
        self.assertEqual(membership.child_group, admins_group)
        self.assertEqual(membership.role, GroupGroupMembership.ADMIN)

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="foobar")
    def test_after_anvil_create_different_admins_group(self):
        admins_group = ManagedGroupFactory.create(name="foobar")
        managed_group = ManagedGroupFactory.create(name="test-group")
        # API response for PRIMED_ADMINS membership.
        self.anvil_response_mock.add(
            responses.PUT,
            self.api_client.sam_entry_point + "/api/groups/v1/test-group/admin/foobar@firecloud.org",
            status=204,
        )
        # Run the adapter method.
        self.adapter.after_anvil_create(managed_group)
        # Check for GroupGroupMembership.
        self.assertEqual(GroupGroupMembership.objects.count(), 1)
        membership = GroupGroupMembership.objects.first()
        self.assertEqual(membership.parent_group, managed_group)
        self.assertEqual(membership.child_group, admins_group)
        self.assertEqual(membership.role, GroupGroupMembership.ADMIN)

    def test_after_anvil_create_no_admins_group(self):
        managed_group = ManagedGroupFactory.create(name="test-group")
        # Run the adapter method.
        self.adapter.after_anvil_create(managed_group)
        # No WorkspaceGroupSharing objects were created.
        self.assertEqual(GroupGroupMembership.objects.count(), 0)
