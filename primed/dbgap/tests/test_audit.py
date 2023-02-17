from datetime import timedelta

from anvil_consortium_manager.tests.factories import (
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
)
from django.test import TestCase
from django.utils import timezone

from .. import audit, models
from . import factories


class AuditResultTest(TestCase):
    """General tests of the AuditResult dataclasses."""

    def test_verified_access(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        audit.VerifiedAccess(
            workspace=dbgap_workspace, data_access_request=dar, note="foo"
        )

    def test_verified_no_access(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        audit.VerifiedNoAccess(
            workspace=dbgap_workspace, data_access_request=dar, note="foo"
        )

    def test_grant_access(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        audit.GrantAccess(
            workspace=dbgap_workspace, data_access_request=dar, note="foo"
        )

    def test_remove_access(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        audit.RemoveAccess(
            workspace=dbgap_workspace, data_access_request=dar, note="foo"
        )

    def test_error(self):
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        audit.Error(workspace=dbgap_workspace, data_access_request=dar, note="foo")


class dbGaPDataAccessSnapshotAuditTest(TestCase):
    """Tests for the dbGaPDataAccessSnapshotAudit class."""

    def test_completed(self):
        """completed is updated properly."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dbgap_snapshot)
        self.assertFalse(dbgap_audit.completed)
        dbgap_audit.run_audit()
        self.assertTrue(dbgap_audit.completed)

    def test_no_workspaces(self):
        """run_audit with no existing workspaces."""
        dar = factories.dbGaPDataAccessRequestFactory.create()
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dar.dbgap_data_access_snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)

    def test_snapshot_has_no_dars(self):
        """run_audit with no dars."""
        # Create a workspace and matching DAR.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dbgap_snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertIsNone(record.data_access_request)
        self.assertEqual(record.note, audit.dbGaPDataAccessSnapshotAudit.NO_DAR)

    def test_one_verified_access(self):
        """run_audit with one workspace that has verified access."""
        # Create a workspace and matching DAR.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace
        )
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory(
            parent_group=auth_domain,
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dar.dbgap_data_access_snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.data_access_request, dar)

    def test_two_verified_access(self):
        """run_audit with two workspaces that have verified access."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        # Create two workspaces and matching DARs.
        auth_domain_1 = ManagedGroupFactory.create()
        dbgap_workspace_1 = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace_1.workspace.authorization_domains.add(auth_domain_1)
        dar_1 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace_1, dbgap_data_access_snapshot=dbgap_snapshot
        )
        auth_domain_2 = ManagedGroupFactory.create()
        dbgap_workspace_2 = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace_2.workspace.authorization_domains.add(auth_domain_2)
        dar_2 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace_2, dbgap_data_access_snapshot=dbgap_snapshot
        )
        # Add the anvil group to the auth groups for the workspaces.
        GroupGroupMembershipFactory(
            parent_group=auth_domain_1,
            child_group=dar_1.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        GroupGroupMembershipFactory(
            parent_group=auth_domain_2,
            child_group=dar_2.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dbgap_snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 2)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedAccess)
        self.assertEqual(record.workspace, dbgap_workspace_1)
        self.assertEqual(record.data_access_request, dar_1)
        record = dbgap_audit.verified[1]
        self.assertIsInstance(record, audit.VerifiedAccess)
        self.assertEqual(record.workspace, dbgap_workspace_2)
        self.assertEqual(record.data_access_request, dar_2)

    def test_one_verified_no_access_dar_not_approved(self):
        """run_audit with one workspace that has verified no access."""
        # Create a workspace and matching DAR.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dar.dbgap_data_access_snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(
            record.note, audit.dbGaPDataAccessSnapshotAudit.DAR_NOT_APPROVED
        )

    def test_grant_access_new_approved_dar(self):
        # Create a workspace and matching DAR.
        # Workspace was created before the snapshot.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create(
            created=timezone.now() - timedelta(weeks=3)
        )
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
        )
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dar.dbgap_data_access_snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(
            record.note, audit.dbGaPDataAccessSnapshotAudit.NEW_APPROVED_DAR
        )

    def test_grant_access_new_workspace(self):
        # Create a workspace and matching DAR.
        # Workspace was created after the snapshot.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create(
            created=timezone.now() - timedelta(weeks=2)
        )
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
        )
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dar.dbgap_data_access_snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(record.note, audit.dbGaPDataAccessSnapshotAudit.NEW_WORKSPACE)

    def test_grant_access_updated_dar(self):
        # Create a workspace and matching DAR.
        # Workspace was created before the snapshot.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create(
            created=timezone.now() - timedelta(weeks=4)
        )
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        # Create an old snapshot where the DAR was not approved.
        old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=old_dar.dbgap_dar_id,
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
        )
        # Do not add the anvil group to the auth group for the workspace.
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dar.dbgap_data_access_snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, audit.GrantAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(
            record.note, audit.dbGaPDataAccessSnapshotAudit.NEW_APPROVED_DAR
        )

    def test_remove_access_udpated_dar(self):
        # Create a workspace and matching DAR.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        # Create an old snapshot where the DAR was approved and a new one where it was closed.
        old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=old_dar.dbgap_dar_id,
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory.create(
            parent_group=auth_domain,
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dar.dbgap_data_access_snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 1)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.needs_action[0]
        self.assertIsInstance(record, audit.RemoveAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(
            record.note, audit.dbGaPDataAccessSnapshotAudit.PREVIOUS_APPROVAL
        )

    def test_error_remove_access_unknown_reason(self):
        """Access needs to be removed for an unknown reason."""
        # Create a workspace and matching DAR.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        # Create an old snapshot where the DAR was rejected and a new one where it is still rejected.
        old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_dar_id=old_dar.dbgap_dar_id,
            dbgap_workspace=dbgap_workspace,
            dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        # Add the anvil group to the auth group for the workspace.
        GroupGroupMembershipFactory.create(
            parent_group=auth_domain,
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dar.dbgap_data_access_snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 1)
        record = dbgap_audit.errors[0]
        self.assertIsInstance(record, audit.RemoveAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(
            record.note, audit.dbGaPDataAccessSnapshotAudit.ERROR_HAS_ACCESS
        )

    def test_error_access_with_no_dar(self):
        """Group has access but there was never any approved DAR."""
        # Create a workspace but no matching DAR.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        # Add the anvil group to the auth group for the workspace.
        snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=auth_domain, child_group=snapshot.dbgap_application.anvil_group
        )
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 0)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 1)
        record = dbgap_audit.errors[0]
        self.assertIsInstance(record, audit.RemoveAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.data_access_request, None)
        self.assertEqual(
            record.note, audit.dbGaPDataAccessSnapshotAudit.ERROR_HAS_ACCESS
        )

    def test_approved_dar_for_different_application(self):
        """There is an approved dar for a different application, but not this one."""
        # Create a workspace and matching DAR.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        # Create an approved DAR from an unrelated application.
        factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace
        )
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
            dbgap_workspace=dbgap_workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        dbgap_audit = audit.dbGaPDataAccessSnapshotAudit(dar.dbgap_data_access_snapshot)
        dbgap_audit.run_audit()
        self.assertEqual(len(dbgap_audit.verified), 1)
        self.assertEqual(len(dbgap_audit.needs_action), 0)
        self.assertEqual(len(dbgap_audit.errors), 0)
        record = dbgap_audit.verified[0]
        self.assertIsInstance(record, audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, dbgap_workspace)
        self.assertEqual(record.data_access_request, dar)
        self.assertEqual(
            record.note, audit.dbGaPDataAccessSnapshotAudit.DAR_NOT_APPROVED
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

    def test_render_action(self):
        """Render action works as expected for grant access types."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        data = [
            {
                "workspace": dbgap_workspace,
                "data_access_request": factories.dbGaPDataAccessRequestForWorkspaceFactory(
                    dbgap_workspace=dbgap_workspace
                ),
                "note": "a note",
                "action": "Grant",
                "action_url": "foo",
            }
        ]
        table = audit.dbGaPAccessAuditTable(data)
        self.assertIsInstance(table, audit.dbGaPAccessAuditTable)
        self.assertEqual(len(table.rows), 1)
        self.assertIn("foo", table.rows[0].get_cell("action"))
        self.assertIn("Grant", table.rows[0].get_cell("action"))
