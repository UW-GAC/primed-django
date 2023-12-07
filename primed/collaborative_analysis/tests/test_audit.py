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
