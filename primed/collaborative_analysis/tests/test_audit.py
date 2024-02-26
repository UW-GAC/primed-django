from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    GroupAccountMembershipFactory,
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
    WorkspaceAuthorizationDomainFactory,
    WorkspaceFactory,
)
from django.test import TestCase
from django.urls import reverse

from primed.cdsa.tests.factories import CDSAWorkspaceFactory
from primed.dbgap.tests.factories import dbGaPWorkspaceFactory

from .. import audit
from . import factories


class WorkspaceAccessAuditResultTest(TestCase):
    def setUp(self):
        super().setUp()

    def test_account_verified_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        account = AccountFactory.create()
        instance = audit.VerifiedAccess(
            collaborative_analysis_workspace=workspace, member=account, note="test"
        )
        expected_url = reverse(
            "collaborative_analysis:audit:resolve",
            args=[
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
                account.email,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)

    def test_account_verified_no_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        account = AccountFactory.create()
        instance = audit.VerifiedNoAccess(
            collaborative_analysis_workspace=workspace, member=account, note="test"
        )
        expected_url = reverse(
            "collaborative_analysis:audit:resolve",
            args=[
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
                account.email,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)

    def test_account_grant_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        account = AccountFactory.create()
        instance = audit.GrantAccess(
            collaborative_analysis_workspace=workspace, member=account, note="test"
        )
        expected_url = reverse(
            "collaborative_analysis:audit:resolve",
            args=[
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
                account.email,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)

    def test_account_remove_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        account = AccountFactory.create()
        instance = audit.RemoveAccess(
            collaborative_analysis_workspace=workspace, member=account, note="test"
        )
        expected_url = reverse(
            "collaborative_analysis:audit:resolve",
            args=[
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
                account.email,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)

    def test_group_verified_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        group = ManagedGroupFactory.create()
        instance = audit.VerifiedAccess(
            collaborative_analysis_workspace=workspace, member=group, note="test"
        )
        expected_url = reverse(
            "collaborative_analysis:audit:resolve",
            args=[
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
                group.email,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)

    def test_group_verified_no_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        group = ManagedGroupFactory.create()
        instance = audit.VerifiedNoAccess(
            collaborative_analysis_workspace=workspace, member=group, note="test"
        )
        expected_url = reverse(
            "collaborative_analysis:audit:resolve",
            args=[
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
                group.email,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)

    def test_group_grant_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        group = ManagedGroupFactory.create()
        instance = audit.GrantAccess(
            collaborative_analysis_workspace=workspace, member=group, note="test"
        )
        expected_url = reverse(
            "collaborative_analysis:audit:resolve",
            args=[
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
                group.email,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)

    def test_group_remove_access(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        group = ManagedGroupFactory.create()
        instance = audit.RemoveAccess(
            collaborative_analysis_workspace=workspace, member=group, note="test"
        )
        expected_url = reverse(
            "collaborative_analysis:audit:resolve",
            args=[
                workspace.workspace.billing_project.name,
                workspace.workspace.name,
                group.email,
            ],
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.NOT_IN_SOURCE_AUTH_DOMAINS)

    def test_analyst_in_collab_auth_domain_two_source_auth_domains_in_both(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        source_auth_domain_2 = WorkspaceAuthorizationDomainFactory.create(
            workspace=source_workspace.workspace
        )
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace.workspace.authorization_domains.all()[0],
            account=account,
        )
        GroupAccountMembershipFactory.create(
            group=source_auth_domain_2.group,
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)

    def test_analyst_in_collab_auth_domain_two_source_auth_domains_in_one(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        WorkspaceAuthorizationDomainFactory.create(workspace=source_workspace.workspace)
        # add an extra auth doamin
        WorkspaceAuthorizationDomainFactory.create(workspace=source_workspace.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace.workspace.authorization_domains.first(),
            account=account,
        )
        # GroupAccountMembershipFactory.create(
        #     group=source_auth_domain_2.group,
        #     account=account,
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.NOT_IN_SOURCE_AUTH_DOMAINS)

    def test_analyst_in_collab_auth_domain_two_source_auth_domains_in_neither(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        WorkspaceAuthorizationDomainFactory.create(workspace=source_workspace.workspace)
        # add an extra auth doamin
        WorkspaceAuthorizationDomainFactory.create(workspace=source_workspace.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace.workspace.authorization_domains.first(),
        #     account=account,
        # )
        # GroupAccountMembershipFactory.create(
        #     group=source_auth_domain_2.group,
        #     account=account,
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.NOT_IN_SOURCE_AUTH_DOMAINS)

    def test_analyst_not_in_collab_auth_domain_two_source_auth_domains_in_both(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        source_auth_domain_1 = source_workspace.workspace.authorization_domains.first()
        source_auth_domain_2 = WorkspaceAuthorizationDomainFactory.create(
            workspace=source_workspace.workspace
        )
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_auth_domain_1,
            account=account,
        )
        GroupAccountMembershipFactory.create(
            group=source_auth_domain_2.group,
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)

    def test_analyst_not_in_collab_auth_domain_two_source_auth_domains_in_one(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        source_auth_domain_2 = WorkspaceAuthorizationDomainFactory.create(
            workspace=source_workspace.workspace
        )
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        # GroupAccountMembershipFactory.create(
        #     group=source_auth_domain_1,
        #     account=account,
        # )
        GroupAccountMembershipFactory.create(
            group=source_auth_domain_2.group,
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
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedNoAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.NOT_IN_SOURCE_AUTH_DOMAINS)

    def test_analyst_not_in_collab_auth_domain_two_source_auth_domains_in_neither(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace.workspace)
        WorkspaceAuthorizationDomainFactory.create(workspace=source_workspace.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        # GroupAccountMembershipFactory.create(
        #     group=source_auth_domain_1,
        #     account=account,
        # )
        # GroupAccountMembershipFactory.create(
        #     group=source_auth_domain_2.group,
        #     account=account,
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.NOT_IN_SOURCE_AUTH_DOMAINS)

    def test_in_collab_auth_domain_no_source_workspaces(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = WorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)

    def test_not_in_collab_auth_domain_no_source_workspaces(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace = WorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)

    def test_in_collab_auth_domain_two_source_workspaces_in_both_auth_domains(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace_1 = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_1.workspace)
        source_workspace_2 = CDSAWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_2.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace_1.workspace.authorization_domains.first(),
            account=account,
        )
        GroupAccountMembershipFactory.create(
            group=source_workspace_2.workspace.authorization_domains.first(),
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)

    def test_in_collab_auth_domain_two_source_workspaces_in_one_auth_domains(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace_1 = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_1.workspace)
        source_workspace_2 = CDSAWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_2.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace_1.workspace.authorization_domains.first(),
            account=account,
        )
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace_2.workspace.authorization_domains.first(),
        #     account=account,
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.NOT_IN_SOURCE_AUTH_DOMAINS)

    def test_in_collab_auth_domain_two_source_workspaces_in_neither_auth_domains(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace_1 = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_1.workspace)
        source_workspace_2 = CDSAWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_2.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace_1.workspace.authorization_domains.first(),
        #     account=account,
        # )
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace_2.workspace.authorization_domains.first(),
        #     account=account,
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.NOT_IN_SOURCE_AUTH_DOMAINS)

    def test_not_in_collab_auth_domain_two_source_workspaces_in_both_auth_domains(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace_1 = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_1.workspace)
        source_workspace_2 = CDSAWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_2.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace_1.workspace.authorization_domains.first(),
            account=account,
        )
        GroupAccountMembershipFactory.create(
            group=source_workspace_2.workspace.authorization_domains.first(),
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)

    def test_not_in_collab_auth_domain_two_source_workspaces_in_one_auth_domains(self):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace_1 = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_1.workspace)
        source_workspace_2 = CDSAWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_2.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        GroupAccountMembershipFactory.create(
            group=source_workspace_1.workspace.authorization_domains.first(),
            account=account,
        )
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace_2.workspace.authorization_domains.first(),
        #     account=account,
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.NOT_IN_SOURCE_AUTH_DOMAINS)

    def test_not_in_collab_auth_domain_two_source_workspaces_in_neither_auth_domains(
        self,
    ):
        # Create accounts.
        account = AccountFactory.create()
        # Set up workspace.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Set up source workspaces.
        source_workspace_1 = dbGaPWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_1.workspace)
        source_workspace_2 = CDSAWorkspaceFactory.create()
        workspace.source_workspaces.add(source_workspace_2.workspace)
        # Analyst group membership.
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=account
        )
        # Source workspace auth domains membership.
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace_1.workspace.authorization_domains.first(),
        #     account=account,
        # )
        # GroupAccountMembershipFactory.create(
        #     group=source_workspace_2.workspace.authorization_domains.first(),
        #     account=account,
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
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collab_audit.NOT_IN_SOURCE_AUTH_DOMAINS)

    def test_two_analysts(self):
        # Create an analyst that needs access.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        analyst_1 = AccountFactory.create()
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=analyst_1
        )
        # Create an analyst that has access.
        analyst_2 = AccountFactory.create()
        GroupAccountMembershipFactory.create(
            group=workspace.analyst_group, account=analyst_2
        )
        GroupAccountMembershipFactory.create(
            group=workspace.workspace.authorization_domains.first(), account=analyst_2
        )
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        collab_audit._audit_workspace(workspace)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 1)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, analyst_2)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, analyst_1)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)

    def test_not_in_analyst_group(self):
        # Create an analyst that needs access.
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Create an analyst that has access but is not in the analyst group.
        analyst = AccountFactory.create()
        GroupAccountMembershipFactory.create(
            group=workspace.workspace.authorization_domains.first(), account=analyst
        )
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        collab_audit._audit_workspace(workspace)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 1)
        record = collab_audit.errors[0]
        self.assertIsInstance(record, audit.RemoveAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, analyst)
        self.assertEqual(record.note, collab_audit.NOT_IN_ANALYST_GROUP)

    def test_unexpected_group_in_auth_domain(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Add a group to the auth domain.
        group = ManagedGroupFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=group,
        )
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        collab_audit._audit_workspace(workspace)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 1)
        record = collab_audit.errors[0]
        self.assertIsInstance(record, audit.RemoveAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, collab_audit.UNEXPECTED_GROUP_ACCESS)

    def test_ignores_primed_admins_group(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Add a group to the auth domain.
        group = ManagedGroupFactory.create(name="PRIMED_CC_ADMINS")
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=group,
        )
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        collab_audit._audit_workspace(workspace)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)

    def test_error_for_primed_cc_members_group(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Add a group to the auth domain.
        group = ManagedGroupFactory.create(name="PRIMED_CC_MEMBERS")
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=group,
        )
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        collab_audit._audit_workspace(workspace)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 1)
        record = collab_audit.errors[0]
        self.assertIsInstance(record, audit.RemoveAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, collab_audit.UNEXPECTED_GROUP_ACCESS)

    def test_no_access_for_primed_cc_members_group(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Add a group to the auth domain.
        ManagedGroupFactory.create(name="PRIMED_CC_MEMBERS")
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=group,
        # )
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        collab_audit._audit_workspace(workspace)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)

    def test_verified_access_for_primed_cc_writers_group(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Add a group to the auth domain.
        group = ManagedGroupFactory.create(name="PRIMED_CC_WRITERS")
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=group,
        )
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        collab_audit._audit_workspace(workspace)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, collab_audit.DCC_ACCESS)

    def test_grant_access_for_primed_cc_writers_group(self):
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        # Add a group to the auth domain.
        group = ManagedGroupFactory.create(name="PRIMED_CC_WRITERS")
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=group,
        # )
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        collab_audit._audit_workspace(workspace)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 1)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, collab_audit.DCC_ACCESS)

    def test_two_workspaces(self):
        # Create a workspace with an analyst that needs access.
        workspace_1 = factories.CollaborativeAnalysisWorkspaceFactory.create()
        analyst_1 = AccountFactory.create()
        GroupAccountMembershipFactory.create(
            group=workspace_1.analyst_group, account=analyst_1
        )
        # Create a workspace with an analyst that has access.
        workspace_2 = factories.CollaborativeAnalysisWorkspaceFactory.create()
        analyst_2 = AccountFactory.create()
        GroupAccountMembershipFactory.create(
            group=workspace_2.analyst_group, account=analyst_2
        )
        GroupAccountMembershipFactory.create(
            group=workspace_2.workspace.authorization_domains.first(), account=analyst_2
        )
        collab_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit()
        collab_audit.run_audit()
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 1)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace_2)
        self.assertEqual(record.member, analyst_2)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace_1)
        self.assertEqual(record.member, analyst_1)
        self.assertEqual(record.note, collab_audit.IN_SOURCE_AUTH_DOMAINS)

    def test_queryset(self):
        """Audit only runs on the specified queryset of workspaces."""
        # Create a workspace with an analyst that needs access.
        workspace_1 = factories.CollaborativeAnalysisWorkspaceFactory.create()
        analyst_1 = AccountFactory.create()
        GroupAccountMembershipFactory.create(
            group=workspace_1.analyst_group, account=analyst_1
        )
        # Create a workspace with an analyst that has access.
        workspace_2 = factories.CollaborativeAnalysisWorkspaceFactory.create()
        analyst_2 = AccountFactory.create()
        GroupAccountMembershipFactory.create(
            group=workspace_2.analyst_group, account=analyst_2
        )
        GroupAccountMembershipFactory.create(
            group=workspace_2.workspace.authorization_domains.first(), account=analyst_2
        )
        collab_audit_1 = audit.CollaborativeAnalysisWorkspaceAccessAudit(
            queryset=[workspace_1]
        )
        collab_audit_1.run_audit()
        self.assertEqual(len(collab_audit_1.verified), 0)
        self.assertEqual(len(collab_audit_1.needs_action), 1)
        self.assertEqual(len(collab_audit_1.errors), 0)
        record = collab_audit_1.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace_1)
        self.assertEqual(record.member, analyst_1)
        self.assertEqual(record.note, collab_audit_1.IN_SOURCE_AUTH_DOMAINS)
        collab_audit_2 = audit.CollaborativeAnalysisWorkspaceAccessAudit(
            queryset=[workspace_2]
        )
        collab_audit_2.run_audit()
        self.assertEqual(len(collab_audit_2.verified), 1)
        self.assertEqual(len(collab_audit_2.needs_action), 0)
        self.assertEqual(len(collab_audit_2.errors), 0)
        record = collab_audit_2.verified[0]
        self.assertIsInstance(record, audit.VerifiedAccess)
        self.assertEqual(record.collaborative_analysis_workspace, workspace_2)
        self.assertEqual(record.member, analyst_2)
        self.assertEqual(record.note, collab_audit_2.IN_SOURCE_AUTH_DOMAINS)


class AccessAuditResultsTableTest(TestCase):
    """Tests for the `AccessAuditResultsTable` table."""

    def test_no_rows(self):
        """Table works with no rows."""
        table = audit.AccessAuditResultsTable([])
        self.assertIsInstance(table, audit.AccessAuditResultsTable)
        self.assertEqual(len(table.rows), 0)

    def test_one_row_account(self):
        """Table works with one row with an account member."""
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        member_account = AccountFactory.create()
        data = [
            {
                "workspace": workspace,
                "member": member_account,
                "note": "a note",
                "action": "",
                "action_url": "",
            }
        ]
        table = audit.AccessAuditResultsTable(data)
        self.assertIsInstance(table, audit.AccessAuditResultsTable)
        self.assertEqual(len(table.rows), 1)

    def test_one_row_group(self):
        """Table works with one row with a group member."""
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        member_group = ManagedGroupFactory.create()
        data = [
            {
                "workspace": workspace,
                "member": member_group,
                "note": "a note",
                "action": "",
                "action_url": "",
            }
        ]
        table = audit.AccessAuditResultsTable(data)
        self.assertIsInstance(table, audit.AccessAuditResultsTable)
        self.assertEqual(len(table.rows), 1)

    def test_two_rows(self):
        """Table works with two rows."""
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        member_account = AccountFactory.create()
        member_group = ManagedGroupFactory.create()
        data = [
            {
                "workspace": workspace,
                "member": member_account,
                "has_access": True,
                "note": "a note",
                "action": "",
                "action_url": "",
            },
            {
                "workspace": workspace,
                "member": member_group,
                "has_access": False,
                "note": "a note",
                "action": "",
                "action_url": "",
            },
        ]
        table = audit.AccessAuditResultsTable(data)
        self.assertIsInstance(table, audit.AccessAuditResultsTable)
        self.assertEqual(len(table.rows), 2)

    def test_render_action(self):
        """Render action works as expected for grant access types."""
        workspace = factories.CollaborativeAnalysisWorkspaceFactory.create()
        member_group = ManagedGroupFactory.create()
        data = [
            {
                "workspace": workspace,
                "member": member_group,
                "note": "a note",
                "action": "Grant",
                "action_url": "foo",
            }
        ]

        table = audit.AccessAuditResultsTable(data)
        self.assertIsInstance(table, audit.AccessAuditResultsTable)
        self.assertEqual(len(table.rows), 1)
        self.assertIn("foo", table.rows[0].get_cell("action"))
        self.assertIn("Grant", table.rows[0].get_cell("action"))
