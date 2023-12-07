from anvil_consortium_manager.tests.factories import AccountFactory
from django.test import TestCase
from django.urls import reverse

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


class CollaborativeAnalysisWorkspaceAccessAudit:
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

    # def test_one(self):
    #     self.fail()
