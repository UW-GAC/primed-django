from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    GroupAccountMembershipFactory,
)
from django.test import TestCase
from django.urls import reverse

from primed.dbgap.tests.factories import dbGaPWorkspaceFactory

from .. import audit
from . import factories


class WorkspaceAccessAuditResultTest(TestCase):
    def setUp(self):
        super().setUp()

    def test_verified_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        account = AccountFactory.create()
        instance = audit.VerifiedAccess(
            workspace=workspace, account=account, note="test"
        )
        self.assertIsNone(instance.get_action_url())

    def test_verified_no_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        account = AccountFactory.create()
        instance = audit.VerifiedNoAccess(
            workspace=workspace, account=account, note="test"
        )
        self.assertIsNone(instance.get_action_url())

    def test_grant_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        account = AccountFactory.create()
        instance = audit.VerifiedAccess(
            workspace=workspace, account=account, note="test"
        )
        expected_url = reverse(
            "anvil_consortium_manager:managed_groups:member_accounts:new_by_account",
            args=[workspace.analyst_group, account],
        )
        self.assertEqual(instance.get_action_url(), expected_url)

    def test_remove_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        account = AccountFactory.create()
        instance = audit.RemoveAccess(workspace=workspace, account=account, note="test")
        expected_url = reverse(
            "anvil_consortium_manager:managed_groups:member_accounts:delete",
            args=[workspace.analyst_group, account],
        )
        self.assertEqual(instance.get_action_url(), expected_url)


class CollaborativeAnalysisWorkspaceAccessAudit(TestCase):
    """Tests for the CollaborativeAnalysisWorkspaceAccessAudit class."""

    def test_completed(self):
        """completed is updated properly."""
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        self.assertFalse(collab_audit.completed)
        collab_audit.run_audit()
        self.assertTrue(collab_audit.completed)

    def test_no_workspaces(self):
        """Audit works if there are no source workspaces."""
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        collab_audit.run_audit()
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)

    def test_one_workspaces_no_analysts(self):
        """Audit works if there are analysts workspaces in the analyst group for a workspace."""
        factories.CollaborativeAnalysisWorkspaceFactory.create()
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        collab_audit.run_audit()
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)

    def test_analyst_in_collab_auth_domain_in_source_auth_domain(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace.workspace.authorization_domains.first(),
            account=account,
        )
        # CollaborativeAnalysisWorkspace auth domain membership.
        GroupAccountMembershipFactory.create(
            group=workspace.workspace.authorization_domains.first(), account=account
        )
        # Set up audit
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        # Run audit
        collab_audit._audit_workspace_and_account(workspace, account)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedAccess)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.account, account)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)

    def test_analyst_in_collab_auth_domain_not_in_source_auth_domain(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace.workspace.authorization_domains.first(), account=account
        # )
        # CollaborativeAnalysisWorkspace auth domain membership.
        GroupAccountMembershipFactory.create(
            group=workspace.workspace.authorization_domains.first(), account=account
        )
        # Set up audit
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        # Run audit
        collab_audit._audit_workspace_and_account(workspace, account)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 1)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, audit.RemoveAccess)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.account, account)
        self.assertEqual(record.note, collab_audit.NOT_IN_SOURCE_AUTH_DOMAINS)

    def test_analyst_not_in_collab_auth_domain_in_source_auth_domain(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace.workspace.authorization_domains.first(),
            account=account,
        )
        # CollaborativeAnalysisWorkspace auth domain membership.
        # GroupAccountMembershipFactory.create(
        #     group=workspace.workspace.authorization_domains.first(), account=account
        # )
        # Set up audit
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        # Run audit
        collab_audit._audit_workspace_and_account(workspace, account)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 1)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.account, account)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)

    def test_analyst_not_in_collab_auth_domain_not_in_source_auth_domain(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace.workspace.authorization_domains.first(), account=account
        # )
        # CollaborativeAnalysisWorkspace auth domain membership.
        # GroupAccountMembershipFactory.create(
        #     group=workspace.workspace.authorization_domains.first(), account=account
        # )
        # Set up audit
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        # Run audit
        collab_audit._audit_workspace_and_account(workspace, account)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.account, account)
        self.assertEqual(record.note, collab_audit.NOT_IN_SOURCE_AUTH_DOMAINS)

    # def test_source_workspace_two_auth_domains(self):
    #     self.fail()

    # def test_workspace_has_no_source_workspaces(self):
    #     self.fail()
