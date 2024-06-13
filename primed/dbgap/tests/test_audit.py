from datetime import timedelta

from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    GroupAccountMembershipFactory,
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
)
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from primed.users.tests.factories import UserFactory

from .. import models
from ..audit import access_audit, collaborator_audit
from . import factories


class AccessAuditResultTest(TestCase):
    """General tests of the AccessAuditResult dataclasses."""

    def test_verified_access(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        instance = access_audit.VerifiedAccess(
            workspace=dbgap_workspace,
            dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            data_access_request=dar,
            note="foo",
        )
        expected_url = reverse(
            "dbgap:audit:access:resolve",
            args=[
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)
        self.assertTrue(instance.has_access)

    def test_verified_no_access(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        instance = access_audit.VerifiedNoAccess(
            workspace=dbgap_workspace,
            dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            data_access_request=dar,
            note="foo",
        )
        expected_url = reverse(
            "dbgap:audit:access:resolve",
            args=[
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)
        self.assertFalse(instance.has_access)

    def test_grant_access(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        instance = access_audit.GrantAccess(
            workspace=dbgap_workspace,
            dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            data_access_request=dar,
            note="foo",
        )
        expected_url = reverse(
            "dbgap:audit:access:resolve",
            args=[
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)
        self.assertFalse(instance.has_access)

    def test_remove_access(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        instance = access_audit.RemoveAccess(
            workspace=dbgap_workspace,
            dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            data_access_request=dar,
            note="foo",
        )
        expected_url = reverse(
            "dbgap:audit:access:resolve",
            args=[
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)
        self.assertTrue(instance.has_access)

    def test_remove_access_no_dar(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_application = factories.dbGaPApplicationFactory.create()
        instance = access_audit.RemoveAccess(
            workspace=dbgap_workspace,
            dbgap_application=dbgap_application,
            note="foo",
        )
        expected_url = reverse(
            "dbgap:audit:access:resolve",
            args=[
                dbgap_application.dbgap_project_id,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)
        self.assertTrue(instance.has_access)

    def test_error(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        instance = access_audit.Error(
            workspace=dbgap_workspace,
            dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            data_access_request=dar,
            note="foo",
            has_access=True,
        )
        expected_url = reverse(
            "dbgap:audit:access:resolve",
            args=[
                dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)

    def test_error_no_dar(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_application = factories.dbGaPApplicationFactory.create()
        instance = access_audit.Error(
            workspace=dbgap_workspace,
            dbgap_application=dbgap_application,
            note="foo",
            has_access=True,
        )
        expected_url = reverse(
            "dbgap:audit:access:resolve",
            args=[
                dbgap_application.dbgap_project_id,
                dbgap_workspace.workspace.billing_project.name,
                dbgap_workspace.workspace.name,
            ],
        )
        self.assertEqual(instance.get_action_url(), expected_url)
        self.assertTrue(instance.has_access)

    def test_post_init(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        other_application = factories.dbGaPApplicationFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        with self.assertRaises(ValueError):
            access_audit.AccessAuditResult(
                workspace=dbgap_workspace,
                dbgap_application=other_application,
                data_access_request=dar,
                note="foo",
                has_access=False,
            )


class dbGaPAccessAuditTest(TestCase):
    """Tests for the dbGaPAccessAudit class."""

    def test_completed(self):
        """completed is updated properly."""
        dbgap_audit = access_audit.dbGaPAccessAudit()
        self.assertFalse(dbgap_audit.completed)
        dbgap_audit.run_audit()
        self.assertTrue(dbgap_audit.completed)

    def test_one_application_no_workspace(self):
        """run_audit with one application and no existing workspaces."""
        factories.dbGaPApplicationFactory.create()
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)

    def test_one_application_one_workspace_no_snapshots(self):
        """run_audit with one application, one workspaces and no snapshots."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, access_audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertIsNone(record.data_access_request)
        self.assertEqual(record.note, access_audit.dbGaPAccessAudit.NO_SNAPSHOTS)

    def test_one_application_one_workspace_snapshot_has_no_dars(self):
        """run_audit with no dars."""
        # Create a workspace and a snapshot.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, access_audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dbgap_snapshot.dbgap_application)
        self.assertIsNone(record.data_access_request)
        self.assertEqual(record.note, access_audit.dbGaPAccessAudit.NO_DAR)

    def test_verified_access(self):
        """run_audit with one application and one workspace that has verified access."""
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=dbgap_workspace)
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, access_audit.VerifiedAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application)
        self.assertEqual(record.data_access_request, dar)
        self.assertTrue(dbgap_audit.ok())

    def test_two_workspaces(self):
        """run_audit with one application and two workspaces with different access."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        # Create two workspaces and matching DARs.
        dbgap_workspace_1 = factories.dbGaPWorkspaceFactory.create()
        dar_1 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace_1, dbgap_data_access_snapshot=dbgap_snapshot
        )
        dbgap_workspace_2 = factories.dbGaPWorkspaceFactory.create()
        dar_2 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace_2, dbgap_data_access_snapshot=dbgap_snapshot
        )
        # Add the anvil group to the auth groups for the first workspace.
        GroupGroupMembershipFactory(
            parent_group=dbgap_workspace_1.workspace.authorization_domains.first(),
            child_group=dar_1.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        # GroupGroupMembershipFactory(
        #     parent_group=dbgap_workspace_2.workspace.authorization_domains.first(),
        #     child_group=dar_2.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        # )
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, access_audit.VerifiedAccess)
        self.assertEqual(record.workspace, dbgap_workspace_1)
        self.assertEqual(record.data_access_request, dar_1)
        self.assertEqual(record.dbgap_application, dbgap_snapshot.dbgap_application)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, access_audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace_2)
        self.assertEqual(record.dbgap_application, dbgap_snapshot.dbgap_application)
        self.assertEqual(record.data_access_request, dar_2)

    def test_verified_no_access_dar_not_approved(self):
        """run_audit with one application and one workspace that has verified no access."""
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, access_audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, access_audit.dbGaPAccessAudit.DAR_NOT_APPROVED)
        self.assertTrue(dbgap_audit.ok())

    def test_verified_no_access_no_dar(self):
        """run_audit with one application and one workspace that has verified no access."""
        # Create a workspace and matching DAR.
        dbgap_application = factories.dbGaPApplicationFactory.create()
        factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=dbgap_application)
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, access_audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertIsNone(record.data_access_request)
        self.assertEqual(record.note, access_audit.dbGaPAccessAudit.NO_DAR)
        self.assertTrue(dbgap_audit.ok())

    def test_grant_access_new_approved_dar(self):
        # Create a workspace and matching DAR.
        # Workspace was created before the snapshot.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create(created=timezone.now() - timedelta(weeks=3))
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
        )
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, access_audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, access_audit.dbGaPAccessAudit.NEW_APPROVED_DAR)
        self.assertFalse(dbgap_audit.ok())

    def test_grant_access_new_workspace(self):
        # Create a workspace and matching DAR.
        # Workspace was created after the snapshot.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create(created=timezone.now() - timedelta(weeks=2))
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
        )
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, access_audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, access_audit.dbGaPAccessAudit.NEW_WORKSPACE)
        self.assertFalse(dbgap_audit.ok())

    def test_grant_access_updated_dar(self):
        # Create a workspace and matching DAR.
        # Workspace was created before the snapshot.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create(created=timezone.now() - timedelta(weeks=4))
        # Create an old snapshot where the DAR was not approved.
        dbgap_application = factories.dbGaPApplicationFactory.create()
        old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__dbgap_application=dbgap_application,
            dbgap_data_access_snapshot__is_most_recent=False,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=old_dar.dbgap_dar_id,
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__dbgap_application=dbgap_application,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
        )
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, access_audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, access_audit.dbGaPAccessAudit.NEW_APPROVED_DAR)
        self.assertFalse(dbgap_audit.ok())

    def test_remove_access_udpated_dar(self):
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Create an old snapshot where the DAR was approved and a new one where it was closed.
        old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__dbgap_application=dbgap_application,
            dbgap_data_access_snapshot__is_most_recent=False,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=old_dar.dbgap_dar_id,
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__dbgap_application=dbgap_application,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory.create(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, access_audit.RemoveAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, access_audit.dbGaPAccessAudit.PREVIOUS_APPROVAL)
        self.assertFalse(dbgap_audit.ok())

    def test_error_remove_access_unknown_reason(self):
        """Access needs to be removed for an unknown reason."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        # Create an old snapshot where the DAR was rejected and a new one where it is still rejected.
        old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__dbgap_application=dbgap_application,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
            dbgap_data_access_snapshot__is_most_recent=False,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=old_dar.dbgap_dar_id,
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__dbgap_application=dbgap_application,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
            dbgap_data_access_snapshot__is_most_recent=True,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory.create(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dbgap_application.anvil_access_group,
        )
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 1)
        record = dbgap_audit.errors[0]
        self.assertIsInstance(record, access_audit.RemoveAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, access_audit.dbGaPAccessAudit.ERROR_HAS_ACCESS)
        self.assertFalse(dbgap_audit.ok())

    def test_error_remove_access_no_snapshot(self):
        """Access needs to be removed for an unknown reason when there is no snapshot."""
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory.create(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dbgap_application.anvil_access_group,
        )
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 1)
        record = dbgap_audit.errors[0]
        self.assertIsInstance(record, access_audit.RemoveAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertIsNone(record.data_access_request)
        self.assertEqual(record.note, access_audit.dbGaPAccessAudit.ERROR_HAS_ACCESS)
        self.assertFalse(dbgap_audit.ok())

    def test_error_remove_access_snapshot_no_dar(self):
        """Group has access but there is no matching DAR."""
        # Create a workspace but no matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        # Add the anvil group to the auth group for the workspace.
        snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=snapshot.dbgap_application.anvil_access_group,
        )
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 1)
        record = dbgap_audit.errors[0]
        self.assertIsInstance(record, access_audit.RemoveAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, snapshot.dbgap_application)
        self.assertIsNone(record.data_access_request)
        self.assertEqual(record.note, access_audit.dbGaPAccessAudit.ERROR_HAS_ACCESS)
        self.assertFalse(dbgap_audit.ok())

    def test_two_applications(self):
        """run_audit with two applications and one workspace."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        # Create two applications and matching DARs.
        dbgap_snapshot_1 = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_snapshot_2 = factories.dbGaPDataAccessSnapshotFactory.create()
        dar_1 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace, dbgap_data_access_snapshot=dbgap_snapshot_1
        )
        dar_2 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace, dbgap_data_access_snapshot=dbgap_snapshot_2
        )
        # Add the anvil group for the first applicatoin to the auth groups for the workspace.
        GroupGroupMembershipFactory(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dbgap_snapshot_1.dbgap_application.anvil_access_group,
        )
        # GroupGroupMembershipFactory(
        #     parent_group=dbgap_workspace.workspace.authorization_domains.first(),
        #     child_group=dbgap_snapshot_2.dbgap_application.anvil_access_group,
        # )
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, access_audit.VerifiedAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dar_1.dbgap_data_access_snapshot.dbgap_application)
        self.assertEqual(record.data_access_request, dar_1)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, access_audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dar_2.dbgap_data_access_snapshot.dbgap_application)
        self.assertEqual(record.data_access_request, dar_2)

    def test_dbgap_application_queryset(self):
        """dbGapAccessAudit only includes the specified dbgap_application_queryset objects."""
        dbgap_application_1 = factories.dbGaPApplicationFactory.create()
        dbgap_application_2 = factories.dbGaPApplicationFactory.create()
        dbgap_application_3 = factories.dbGaPApplicationFactory.create()
        dbgap_audit = access_audit.dbGaPAccessAudit(
            dbgap_application_queryset=models.dbGaPApplication.objects.filter(
                pk__in=[dbgap_application_1.pk, dbgap_application_2.pk]
            )
        )
        self.assertEqual(dbgap_audit.dbgap_application_queryset.count(), 2)
        self.assertIn(dbgap_application_1, dbgap_audit.dbgap_application_queryset)
        self.assertIn(dbgap_application_2, dbgap_audit.dbgap_application_queryset)
        self.assertNotIn(dbgap_application_3, dbgap_audit.dbgap_application_queryset)

    def test_dbgap_workspace_queryset(self):
        """dbGapAccessAudit only includes the specified dbgap_application_queryset objects."""
        dbgap_workspace_1 = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace_2 = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace_3 = factories.dbGaPWorkspaceFactory.create()
        dbgap_audit = access_audit.dbGaPAccessAudit(
            dbgap_workspace_queryset=models.dbGaPWorkspace.objects.filter(
                pk__in=[dbgap_workspace_1.pk, dbgap_workspace_2.pk]
            )
        )
        self.assertEqual(dbgap_audit.dbgap_workspace_queryset.count(), 2)
        self.assertIn(dbgap_workspace_1, dbgap_audit.dbgap_workspace_queryset)
        self.assertIn(dbgap_workspace_2, dbgap_audit.dbgap_workspace_queryset)
        self.assertNotIn(dbgap_workspace_3, dbgap_audit.dbgap_workspace_queryset)

    def test_dbgap_workspace_queryset_wrong_class(self):
        """dbGaPAccessAudit raises error if dbgap_workspace_queryset has the wrong model class."""
        with self.assertRaises(ValueError) as e:
            access_audit.dbGaPAccessAudit(dbgap_workspace_queryset=models.dbGaPApplication.objects.all())
        self.assertEqual(
            str(e.exception),
            "dbgap_workspace_queryset must be a queryset of dbGaPWorkspace objects.",
        )

    def test_dbgap_workspace_queryset_not_queryset(self):
        """dbGaPAccessAudit raises error if dbgap_workspace_queryset is not a queryset."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        with self.assertRaises(ValueError) as e:
            access_audit.dbGaPAccessAudit(dbgap_workspace_queryset=dbgap_workspace)
        self.assertEqual(
            str(e.exception),
            "dbgap_workspace_queryset must be a queryset of dbGaPWorkspace objects.",
        )

    def test_dbgap_application_queryset_wrong_class(self):
        """dbGaPAccessAudit raises error if dbgap_application_queryset has the wrong model class."""
        with self.assertRaises(ValueError) as e:
            access_audit.dbGaPAccessAudit(dbgap_application_queryset=models.dbGaPWorkspace.objects.all())
        self.assertEqual(
            str(e.exception),
            "dbgap_application_queryset must be a queryset of dbGaPApplication objects.",
        )

    def test_dbgap_application_queryset_not_queryset(self):
        """dbGaPAccessAudit raises error if dbgap_application_queryset is not a queryset."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        with self.assertRaises(ValueError) as e:
            access_audit.dbGaPAccessAudit(dbgap_application_queryset=dbgap_application)
        self.assertEqual(
            str(e.exception),
            "dbgap_application_queryset must be a queryset of dbGaPApplication objects.",
        )

    def test_two_applications_two_workspaces(self):
        pass

    def test_ok_with_verified_and_needs_action(self):
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        other_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=dbgap_workspace)
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=other_dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=dbgap_workspace)
        # # Add the anvil group to the auth group for the workspace.
        # GroupGroupMembershipFactory(
        #     parent_group=dbgap_workspace.workspace.authorization_domains.first(),
        #     child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        # )
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertFalse(dbgap_audit.ok())

    def test_ok_with_verified_and_error(self):
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        other_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(dbgap_workspace=dbgap_workspace)
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=other_dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
        #     dbgap_workspace=dbgap_workspace
        # )
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dbgap_application.anvil_access_group,
        )
        dbgap_audit = access_audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.errors), 1)
        self.assertFalse(dbgap_audit.ok())

    def test_ok_not_completed(self):
        dbgap_audit = access_audit.dbGaPAccessAudit()
        with self.assertRaises(ValueError) as e:
            dbgap_audit.ok()
        self.assertEqual(
            str(e.exception),
            "Audit has not been completed. Use run_audit() to run the audit.",
        )


class dbGaPAccessAuditTableTest(TestCase):
    """Tests for the `dbGaPAccessAuditTableTest` table."""

    def test_no_rows(self):
        """Table works with no rows."""
        table = access_audit.dbGaPAccessAuditTable([])
        self.assertIsInstance(table, access_audit.dbGaPAccessAuditTable)
        self.assertEqual(len(table.rows), 0)

    def test_one_row(self):
        """Table works with one row."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        data = [
            {
                "workspace": dbgap_workspace,
                "data_access_request": factories.dbGaPDataAccessRequestForWorkspaceFactory(
                    dbgap_workspace=dbgap_workspace
                ),
                "note": "a note",
                "action": "",
                "action_url": "",
            }
        ]
        table = access_audit.dbGaPAccessAuditTable(data)
        self.assertIsInstance(table, access_audit.dbGaPAccessAuditTable)
        self.assertEqual(len(table.rows), 1)

    def test_two_rows(self):
        """Table works with two rows."""
        dbgap_workspace_1 = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace_2 = factories.dbGaPWorkspaceFactory.create()
        data = [
            {
                "workspace": dbgap_workspace_1,
                "data_access_request": factories.dbGaPDataAccessRequestForWorkspaceFactory(
                    dbgap_workspace=dbgap_workspace_1
                ),
                "note": "a note",
                "action": "",
                "action_url": "",
            },
            {
                "workspace": dbgap_workspace_2,
                "data_access_request": factories.dbGaPDataAccessRequestForWorkspaceFactory(
                    dbgap_workspace=dbgap_workspace_2
                ),
                "note": "a note",
                "action": "",
                "action_url": "",
            },
        ]
        table = access_audit.dbGaPAccessAuditTable(data)
        self.assertIsInstance(table, access_audit.dbGaPAccessAuditTable)
        self.assertEqual(len(table.rows), 2)


class CollaboratorAuditResultTest(TestCase):
    """General tests of the CollaboratorAuditResult dataclasses."""

    def test_write_tests(self):
        self.fail()


class dbGaPCollaboratorAuditTableTest(TestCase):
    """General tests of the CollaboratorAuditTable class.."""

    def test_write_tests(self):
        self.fail()


class dbGaPCollaboratorAuditTest(TestCase):
    """Tests for the CollaboratorAuditResult dataclasses."""

    def test_completed(self):
        """completed is updated properly."""
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        self.assertFalse(collab_audit.completed)
        collab_audit.run_audit()
        self.assertTrue(collab_audit.completed)

    def test_no_applications(self):
        """Audit works if there are no dbGaPApplications."""
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.run_audit()
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)

    def test_audit_application_and_object_user(self):
        """audit_application_and_object works when passed a user object."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        user = UserFactory.create()
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.audit_application_and_object(dbgap_application, user)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.NOT_COLLABORATOR)

    def test_audit_application_and_object_account(self):
        """audit_application_and_object works when passed an Account object."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        account = AccountFactory.create()
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.audit_application_and_object(dbgap_application, account)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_audit_application_and_object_group(self):
        """audit_application_and_object works when passed a ManagedGroup object."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        group = ManagedGroupFactory.create()
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.audit_application_and_object(dbgap_application, group)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.GROUP_WITHOUT_ACCESS)

    def test_audit_application_and_object_user_email(self):
        """audit_application_and_object works when passed a string email for a user."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        user = UserFactory.create()
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.audit_application_and_object(dbgap_application, user.username)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.NOT_COLLABORATOR)

    def test_audit_application_and_object_user_email_case_insensitive(self):
        """audit_application_and_object works when passed a string email for a user."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        user = UserFactory.create(username="foo@BAR.com")
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.audit_application_and_object(dbgap_application, "FOO@bar.com")
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.NOT_COLLABORATOR)

    def test_audit_application_and_object_account_email(self):
        """audit_application_and_object works when passed a string email for an account."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        account = AccountFactory.create()
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.audit_application_and_object(dbgap_application, account.email)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_audit_application_and_object_account_email_case_insensitive(self):
        """audit_application_and_object works when passed a string email for an account."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        account = AccountFactory.create(email="foo@BAR.com")
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.audit_application_and_object(dbgap_application, "FOO@bar.com")
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_audit_application_and_object_group_email(self):
        """audit_application_and_object works when passed a string email for a ManagedGroup."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        group = ManagedGroupFactory.create()
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.audit_application_and_object(dbgap_application, group.email)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.GROUP_WITHOUT_ACCESS)

    def test_audit_application_and_object_group_email_case_insensitive(self):
        """audit_application_and_object works when passed a string email for a ManagedGroup."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        group = ManagedGroupFactory.create(email="foo@BAR.com")
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.audit_application_and_object(dbgap_application, "FOO@bar.com")
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.GROUP_WITHOUT_ACCESS)

    def test_audit_application_and_object_email_does_not_exist(self):
        """audit_application_and_object works when passed a ManagedGroup object."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        with self.assertRaises(ValueError) as e:
            collab_audit.audit_application_and_object(dbgap_application, "foo@bar.com")
        self.assertIn(
            "Could not find",
            str(e.exception),
        )

    def test_pi_no_account(self):
        """Audit works if the PI has not linked their account."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.run_audit()
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, dbgap_application.principal_investigator)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.PI_NO_ACCOUNT)

    def test_pi_linked_account_not_in_access_group(self):
        """PI has linked their account but is not in the access group."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        account = AccountFactory.create(user=dbgap_application.principal_investigator)
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.run_audit()
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 1)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, collaborator_audit.GrantAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, dbgap_application.principal_investigator)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.PI_LINKED_ACCOUNT)

    def test_pi_linked_account_in_access_group(self):
        """PI has linked their account and is in the access group."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        account = AccountFactory.create(user=dbgap_application.principal_investigator)
        GroupAccountMembershipFactory.create(account=account, group=dbgap_application.anvil_access_group)
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.run_audit()
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, dbgap_application.principal_investigator)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.PI_IN_ACCESS_GROUP)

    def test_collaborator_linked_account_in_access_group(self):
        # Create applications.
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up collaborators.
        dbgap_application.collaborators.add(account.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=dbgap_application.anvil_access_group, account=account)
        # Set up audit
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        # Run audit
        collab_audit.audit_application_and_object(dbgap_application, account.user)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.COLLABORATOR_IN_ACCESS_GROUP)

    def test_collaborator_linked_account_not_in_access_group(self):
        # Create applications.
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up collaborators.
        dbgap_application.collaborators.add(account.user)
        # Access group membership.
        # GroupAccountMembershipFactory.create(group=dbgap_application.anvil_access_group, account=account)
        # Set up audit
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        # Run audit
        collab_audit.audit_application_and_object(dbgap_application, account.user)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 1)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, collaborator_audit.GrantAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.COLLABORATOR_LINKED_ACCOUNT)

    def test_collaborator_no_account(self):
        # Create applications.
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Create accounts.
        user = UserFactory.create()
        # account = AccountFactory.create(verified=True)
        # Set up collaborators.
        dbgap_application.collaborators.add(user)
        # Access group membership.
        # GroupAccountMembershipFactory.create(group=dbgap_application.anvil_access_group, account=account)
        # Set up audit
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        # Run audit
        collab_audit.audit_application_and_object(dbgap_application, user)
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.COLLABORATOR_NO_ACCOUNT)

    def test_user_in_group_not_collaborator(self):
        # Create applications.
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up collaborators.
        # dbgap_application.collaborators.add(account.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=dbgap_application.anvil_access_group, account=account)
        # Set up audit
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        # Run audit
        collab_audit.audit_application_and_object(dbgap_application, account.user)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 1)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, collaborator_audit.RemoveAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.NOT_COLLABORATOR)

    def test_not_collaborator_and_account_has_no_user(self):
        # Create applications.
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Create accounts.
        account = AccountFactory.create()
        # Set up collaborators.
        # dbgap_application.collaborators.add(account.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=dbgap_application.anvil_access_group, account=account)
        # Set up audit
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        # Run audit
        collab_audit.audit_application_and_object(dbgap_application, account)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 1)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, collaborator_audit.RemoveAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_two_collaborators(self):
        """Audit works when there are two collaborators."""
        # Create applications.
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Create accounts.
        account_1 = AccountFactory.create(verified=True)
        account_2 = AccountFactory.create(verified=True)
        # Set up collaborators.
        dbgap_application.collaborators.add(account_1.user, account_2.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=dbgap_application.anvil_access_group, account=account_1)
        # Set up audit
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        # Run audit
        collab_audit.audit_application(dbgap_application)
        self.assertEqual(len(collab_audit.verified), 2)  # The PI and one of the collaborators.
        self.assertEqual(len(collab_audit.needs_action), 1)  # The other collaborator.
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[1]  # The 0th record is the PI.
        self.assertIsInstance(record, collaborator_audit.VerifiedAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, account_1.user)
        self.assertEqual(record.member, account_1)
        self.assertEqual(record.note, collab_audit.COLLABORATOR_IN_ACCESS_GROUP)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, collaborator_audit.GrantAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, account_2.user)
        self.assertEqual(record.member, account_2)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.COLLABORATOR_LINKED_ACCOUNT)

    def test_unexpected_group_in_access_group(self):
        """A group unexpectedly has access."""
        # Create applications.
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Add a group to the access group.
        group = ManagedGroupFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=dbgap_application.anvil_access_group,
            child_group=group,
        )
        # Set up audit
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        # Run audit
        collab_audit.audit_application(dbgap_application)
        self.assertEqual(len(collab_audit.verified), 1)  # The PI.
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 1)
        record = collab_audit.errors[0]
        self.assertIsInstance(record, collaborator_audit.RemoveAccess)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.UNEXPECTED_GROUP_ACCESS)

    def test_ignores_admins_group(self):
        """A group unexpectedly has access."""
        # Create applications.
        dbgap_application = factories.dbGaPApplicationFactory.create()
        # Add a group to the access group.
        group = ManagedGroupFactory.create(name="PRIMED_CC_ADMINS")
        GroupGroupMembershipFactory.create(
            parent_group=dbgap_application.anvil_access_group,
            child_group=group,
        )
        # Set up audit
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        # Run audit
        collab_audit.audit_application(dbgap_application)
        self.assertEqual(len(collab_audit.verified), 1)  # The PI.
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        # Check the sub-method specifically.
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.audit_application_and_object(dbgap_application, group)
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)

    def test_two_applications(self):
        """Audit works with two dbGaPApplications."""
        dbgap_application_1 = factories.dbGaPApplicationFactory.create()
        account_1 = AccountFactory.create(user=dbgap_application_1.principal_investigator)
        dbgap_application_2 = factories.dbGaPApplicationFactory.create()
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit()
        collab_audit.run_audit()
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 1)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application_2)
        self.assertEqual(record.user, dbgap_application_2.principal_investigator)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.PI_NO_ACCOUNT)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, collaborator_audit.GrantAccess)
        self.assertEqual(record.dbgap_application, dbgap_application_1)
        self.assertEqual(record.user, dbgap_application_1.principal_investigator)
        self.assertEqual(record.member, account_1)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.PI_LINKED_ACCOUNT)

    def test_queryset(self):
        """Audit only runs on the specified queryset of dbGaPApplications."""
        dbgap_application_1 = factories.dbGaPApplicationFactory.create()
        account_1 = AccountFactory.create(user=dbgap_application_1.principal_investigator)
        dbgap_application_2 = factories.dbGaPApplicationFactory.create()
        # First application
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit(
            queryset=models.dbGaPApplication.objects.filter(pk=dbgap_application_1.pk)
        )
        collab_audit.run_audit()
        self.assertEqual(len(collab_audit.verified), 0)
        self.assertEqual(len(collab_audit.needs_action), 1)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.needs_action[0]
        self.assertIsInstance(record, collaborator_audit.GrantAccess)
        self.assertEqual(record.dbgap_application, dbgap_application_1)
        self.assertEqual(record.user, dbgap_application_1.principal_investigator)
        self.assertEqual(record.member, account_1)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.PI_LINKED_ACCOUNT)
        # Second application
        collab_audit = collaborator_audit.dbGaPCollaboratorAudit(
            queryset=models.dbGaPApplication.objects.filter(pk=dbgap_application_2.pk)
        )
        collab_audit.run_audit()
        self.assertEqual(len(collab_audit.verified), 1)
        self.assertEqual(len(collab_audit.needs_action), 0)
        self.assertEqual(len(collab_audit.errors), 0)
        record = collab_audit.verified[0]
        self.assertIsInstance(record, collaborator_audit.VerifiedNoAccess)
        self.assertEqual(record.dbgap_application, dbgap_application_2)
        self.assertEqual(record.user, dbgap_application_2.principal_investigator)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, collaborator_audit.dbGaPCollaboratorAudit.PI_NO_ACCOUNT)
