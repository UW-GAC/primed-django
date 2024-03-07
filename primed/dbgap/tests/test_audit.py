from datetime import timedelta

from anvil_consortium_manager.tests.factories import GroupGroupMembershipFactory
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .. import audit, models
from . import factories


class AuditResultTest(TestCase):
    """General tests of the AuditResult dataclasses."""

    def test_verified_access(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        instance = audit.VerifiedAccess(
            workspace=dbgap_workspace,
            dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            data_access_request=dar,
            note="foo",
        )
        expected_url = reverse(
            "dbgap:audit:resolve",
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
        instance = audit.VerifiedNoAccess(
            workspace=dbgap_workspace,
            dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            data_access_request=dar,
            note="foo",
        )
        expected_url = reverse(
            "dbgap:audit:resolve",
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
        instance = audit.GrantAccess(
            workspace=dbgap_workspace,
            dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            data_access_request=dar,
            note="foo",
        )
        expected_url = reverse(
            "dbgap:audit:resolve",
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
        instance = audit.RemoveAccess(
            workspace=dbgap_workspace,
            dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            data_access_request=dar,
            note="foo",
        )
        expected_url = reverse(
            "dbgap:audit:resolve",
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
        instance = audit.RemoveAccess(
            workspace=dbgap_workspace,
            dbgap_application=dbgap_application,
            note="foo",
        )
        expected_url = reverse(
            "dbgap:audit:resolve",
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
        instance = audit.Error(
            workspace=dbgap_workspace,
            dbgap_application=dar.dbgap_data_access_snapshot.dbgap_application,
            data_access_request=dar,
            note="foo",
            has_access=True,
        )
        expected_url = reverse(
            "dbgap:audit:resolve",
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
        instance = audit.Error(
            workspace=dbgap_workspace,
            dbgap_application=dbgap_application,
            note="foo",
            has_access=True,
        )
        expected_url = reverse(
            "dbgap:audit:resolve",
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
            audit.AuditResult(
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
        dbgap_audit = audit.dbGaPAccessAudit()
        self.assertFalse(dbgap_audit.completed)
        dbgap_audit.run_audit()
        self.assertTrue(dbgap_audit.completed)

    def test_one_application_no_workspace(self):
        """run_audit with one application and no existing workspaces."""
        factories.dbGaPApplicationFactory.create()
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)

    def test_one_application_one_workspace_no_snapshots(self):
        """run_audit with one application, one workspaces and no snapshots."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertIsNone(record.data_access_request)
        self.assertEqual(record.note, audit.dbGaPAccessAudit.NO_SNAPSHOTS)

    def test_one_application_one_workspace_snapshot_has_no_dars(self):
        """run_audit with no dars."""
        # Create a workspace and a snapshot.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dbgap_snapshot.dbgap_application)
        self.assertIsNone(record.data_access_request)
        self.assertEqual(record.note, audit.dbGaPAccessAudit.NO_DAR)

    def test_verified_access(self):
        """run_audit with one application and one workspace that has verified access."""
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace
        )
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(
            record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
        )
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
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedAccess)
        self.assertEqual(record.workspace, dbgap_workspace_1)
        self.assertEqual(record.data_access_request, dar_1)
        self.assertEqual(record.dbgap_application, dbgap_snapshot.dbgap_application)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
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
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(
            record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
        )
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, audit.dbGaPAccessAudit.DAR_NOT_APPROVED)
        self.assertTrue(dbgap_audit.ok())

    def test_verified_no_access_no_dar(self):
        """run_audit with one application and one workspace that has verified no access."""
        # Create a workspace and matching DAR.
        dbgap_application = factories.dbGaPApplicationFactory.create()
        factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application
        )
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertIsNone(record.data_access_request)
        self.assertEqual(record.note, audit.dbGaPAccessAudit.NO_DAR)
        self.assertTrue(dbgap_audit.ok())

    def test_grant_access_new_approved_dar(self):
        # Create a workspace and matching DAR.
        # Workspace was created before the snapshot.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create(
            created=timezone.now() - timedelta(weeks=3)
        )
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
        )
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(
            record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
        )
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, audit.dbGaPAccessAudit.NEW_APPROVED_DAR)
        self.assertFalse(dbgap_audit.ok())

    def test_grant_access_new_workspace(self):
        # Create a workspace and matching DAR.
        # Workspace was created after the snapshot.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create(
            created=timezone.now() - timedelta(weeks=2)
        )
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
        )
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(
            record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
        )
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, audit.dbGaPAccessAudit.NEW_WORKSPACE)
        self.assertFalse(dbgap_audit.ok())

    def test_grant_access_updated_dar(self):
        # Create a workspace and matching DAR.
        # Workspace was created before the snapshot.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create(
            created=timezone.now() - timedelta(weeks=4)
        )
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
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(
            record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
        )
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, audit.dbGaPAccessAudit.NEW_APPROVED_DAR)
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
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, audit.RemoveAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(
            record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
        )
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, audit.dbGaPAccessAudit.PREVIOUS_APPROVAL)
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
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 1)
        record = dbgap_audit.errors[0]
        self.assertIsInstance(record, audit.RemoveAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, audit.dbGaPAccessAudit.ERROR_HAS_ACCESS)
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
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 1)
        record = dbgap_audit.errors[0]
        self.assertIsInstance(record, audit.RemoveAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, dbgap_application)
        self.assertIsNone(record.data_access_request)
        self.assertEqual(record.note, audit.dbGaPAccessAudit.ERROR_HAS_ACCESS)
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
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 1)
        record = dbgap_audit.errors[0]
        self.assertIsInstance(record, audit.RemoveAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.dbgap_application, snapshot.dbgap_application)
        self.assertIsNone(record.data_access_request)
        self.assertEqual(record.note, audit.dbGaPAccessAudit.ERROR_HAS_ACCESS)
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
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(
            record.dbgap_application, dar_1.dbgap_data_access_snapshot.dbgap_application
        )
        self.assertEqual(record.data_access_request, dar_1)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(
            record.dbgap_application, dar_2.dbgap_data_access_snapshot.dbgap_application
        )
        self.assertEqual(record.data_access_request, dar_2)

    def test_dbgap_application_queryset(self):
        """dbGapAccessAudit only includes the specified dbgap_application_queryset objects."""
        dbgap_application_1 = factories.dbGaPApplicationFactory.create()
        dbgap_application_2 = factories.dbGaPApplicationFactory.create()
        dbgap_application_3 = factories.dbGaPApplicationFactory.create()
        dbgap_audit = audit.dbGaPAccessAudit(
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
        dbgap_audit = audit.dbGaPAccessAudit(
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
            audit.dbGaPAccessAudit(
                dbgap_workspace_queryset=models.dbGaPApplication.objects.all()
            )
        self.assertEqual(
            str(e.exception),
            "dbgap_workspace_queryset must be a queryset of dbGaPWorkspace objects.",
        )

    def test_dbgap_workspace_queryset_not_queryset(self):
        """dbGaPAccessAudit raises error if dbgap_workspace_queryset is not a queryset."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        with self.assertRaises(ValueError) as e:
            audit.dbGaPAccessAudit(dbgap_workspace_queryset=dbgap_workspace)
        self.assertEqual(
            str(e.exception),
            "dbgap_workspace_queryset must be a queryset of dbGaPWorkspace objects.",
        )

    def test_dbgap_application_queryset_wrong_class(self):
        """dbGaPAccessAudit raises error if dbgap_application_queryset has the wrong model class."""
        with self.assertRaises(ValueError) as e:
            audit.dbGaPAccessAudit(
                dbgap_application_queryset=models.dbGaPWorkspace.objects.all()
            )
        self.assertEqual(
            str(e.exception),
            "dbgap_application_queryset must be a queryset of dbGaPApplication objects.",
        )

    def test_dbgap_application_queryset_not_queryset(self):
        """dbGaPAccessAudit raises error if dbgap_application_queryset is not a queryset."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        with self.assertRaises(ValueError) as e:
            audit.dbGaPAccessAudit(dbgap_application_queryset=dbgap_application)
        self.assertEqual(
            str(e.exception),
            "dbgap_application_queryset must be a queryset of dbGaPApplication objects.",
        )

    def test_two_applications_two_workspaces(self):
        pass

    def test_ok_with_verified_and_needs_action(self):
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        other_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace
        )
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory(
            parent_group=dbgap_workspace.workspace.authorization_domains.first(),
            child_group=other_dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace
        )
        # # Add the anvil group to the auth group for the workspace.
        # GroupGroupMembershipFactory(
        #     parent_group=dbgap_workspace.workspace.authorization_domains.first(),
        #     child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        # )
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertFalse(dbgap_audit.ok())

    def test_ok_with_verified_and_error(self):
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        other_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace
        )
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
        dbgap_audit = audit.dbGaPAccessAudit()
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.errors), 1)
        self.assertFalse(dbgap_audit.ok())

    def test_ok_not_completed(self):
        dbgap_audit = audit.dbGaPAccessAudit()
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
        table = audit.dbGaPAccessAuditTable([])
        self.assertIsInstance(table, audit.dbGaPAccessAuditTable)
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
        table = audit.dbGaPAccessAuditTable(data)
        self.assertIsInstance(table, audit.dbGaPAccessAuditTable)
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
        table = audit.dbGaPAccessAuditTable(data)
        self.assertIsInstance(table, audit.dbGaPAccessAuditTable)
        self.assertEqual(len(table.rows), 2)
