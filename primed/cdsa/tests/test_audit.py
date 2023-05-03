# from datetime import timedelta

from anvil_consortium_manager.tests.factories import (  # GroupGroupMembershipFactory,; ManagedGroupFactory,
    ManagedGroupFactory,
)
from django.test import TestCase

from .. import audit
from . import factories

# from django.utils import timezone


class SignedAgreementAuditResultTest(TestCase):
    """General tests of the AuditResult dataclasses."""

    def setUp(self):
        super().setUp()
        ManagedGroupFactory.objects.create(name="PRIMED_CDSA")

    def test_verified_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        audit.VerifiedAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )

    def test_verified_no_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        audit.VerifiedNoAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )

    def test_grant_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = audit.GrantAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        instance.get_action_url()

    def test_remove_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = audit.RemoveAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        instance.get_action_url()

    def test_remove_access_no_dar(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = audit.RemoveAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        instance.get_action_url()

    def test_error(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = audit.Error(
            signed_agreement=signed_agreement,
            note="foo",
        )
        instance.get_action_url()

    def test_error_no_dar(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = audit.Error(
            signed_agreement=signed_agreement,
            note="foo",
        )
        instance.get_action_url()


# class dbGaPApplicationAccessAuditTest(TestCase):
#     """Tests for the dbGaPApplicationAccessAudit class."""
#
#     def test_completed(self):
#         """completed is updated properly."""
#         dbgap_application = factories.dbGaPApplicationFactory.create()
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(dbgap_application)
#         self.assertFalse(dbgap_audit.completed)
#         dbgap_audit.run_audit()
#         self.assertTrue(dbgap_audit.completed)
#
#     def test_no_workspaces_no_snapshots(self):
#         """run_audit with no existing workspaces and no snapshots."""
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dbgap_application = factories.dbGaPApplicationFactory.create()
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(dbgap_application)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 1)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedNoAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(record.dbgap_application, dbgap_application)
#         self.assertIsNone(record.data_access_request)
#         self.assertEqual(record.note, audit.dbGaPAccessAudit.NO_SNAPSHOTS)
#
#     def test_one_workspaces_no_snapshots(self):
#         """run_audit with no existing workspaces and no snapshots."""
#         dbgap_application = factories.dbGaPApplicationFactory.create()
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(dbgap_application)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#
#     def test_snapshot_has_no_dars(self):
#         """run_audit with no dars."""
#         # Create a workspace and a snapshot.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(
#             dbgap_snapshot.dbgap_application
#         )
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 1)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedNoAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(record.dbgap_application, dbgap_snapshot.dbgap_application)
#         self.assertIsNone(record.data_access_request)
#         self.assertEqual(record.note, audit.dbGaPAccessAudit.NO_DAR)
#
#     def test_one_verified_access(self):
#         """run_audit with one workspace that has verified access."""
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace
#         )
#         # Add the anvil group to the auth group for the workspace.
#         GroupGroupMembershipFactory(
#             parent_group=auth_domain,
#             child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(
#             dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 1)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#
#     def test_two_verified_access(self):
#         """run_audit with two workspaces that have verified access."""
#         dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
#         # Create two workspaces and matching DARs.
#         auth_domain_1 = ManagedGroupFactory.create()
#         cdsa_workspace_1 = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace_1.workspace.authorization_domains.add(auth_domain_1)
#         dar_1 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace_1, dbgap_data_access_snapshot=dbgap_snapshot
#         )
#         auth_domain_2 = ManagedGroupFactory.create()
#         cdsa_workspace_2 = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace_2.workspace.authorization_domains.add(auth_domain_2)
#         dar_2 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace_2, dbgap_data_access_snapshot=dbgap_snapshot
#         )
#         # Add the anvil group to the auth groups for the workspaces.
#         GroupGroupMembershipFactory(
#             parent_group=auth_domain_1,
#             child_group=dar_1.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
#         )
#         GroupGroupMembershipFactory(
#             parent_group=auth_domain_2,
#             child_group=dar_2.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(
#             dbgap_snapshot.dbgap_application
#         )
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 2)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedAccess)
#         self.assertEqual(record.workspace, cdsa_workspace_1)
#         self.assertEqual(record.data_access_request, dar_1)
#         self.assertEqual(record.dbgap_application, dbgap_snapshot.dbgap_application)
#         record = dbgap_audit.verified[1]
#         self.assertIsInstance(record, audit.VerifiedAccess)
#         self.assertEqual(record.workspace, cdsa_workspace_2)
#         self.assertEqual(record.dbgap_application, dbgap_snapshot.dbgap_application)
#         self.assertEqual(record.data_access_request, dar_2)
#
#     def test_one_verified_no_access_dar_not_approved(self):
#         """run_audit with one workspace that has verified no access."""
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
#         )
#         # Do not add the anvil group to the auth group for the workspace.
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(
#             dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 1)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedNoAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.DAR_NOT_APPROVED
#         )
#
#     def test_grant_access_new_approved_dar(self):
#         # Create a workspace and matching DAR.
#         # Workspace was created before the snapshot.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create(
#             created=timezone.now() - timedelta(weeks=3)
#         )
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
#         )
#         # Do not add the anvil group to the auth group for the workspace.
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(
#             dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 1)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.needs_action[0]
#         self.assertIsInstance(record, audit.GrantAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.NEW_APPROVED_DAR
#         )
#
#     def test_grant_access_new_workspace(self):
#         # Create a workspace and matching DAR.
#         # Workspace was created after the snapshot.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create(
#             created=timezone.now() - timedelta(weeks=2)
#         )
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
#         )
#         # Do not add the anvil group to the auth group for the workspace.
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(
#             dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 1)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.needs_action[0]
#         self.assertIsInstance(record, audit.GrantAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(record.note, audit.dbGaPApplicationAccessAudit.NEW_WORKSPACE)
#
#     def test_grant_access_updated_dar(self):
#         # Create a workspace and matching DAR.
#         # Workspace was created before the snapshot.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create(
#             created=timezone.now() - timedelta(weeks=4)
#         )
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         # Create an old snapshot where the DAR was not approved.
#         dbgap_application = factories.dbGaPApplicationFactory.create()
#         old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__dbgap_application=dbgap_application,
#             dbgap_data_access_snapshot__is_most_recent=False,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
#             dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
#         )
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             dbgap_dar_id=old_dar.dbgap_dar_id,
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__dbgap_application=dbgap_application,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
#         )
#         # Do not add the anvil group to the auth group for the workspace.
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(
#             dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 1)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.needs_action[0]
#         self.assertIsInstance(record, audit.GrantAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.NEW_APPROVED_DAR
#         )
#
#     def test_remove_access_udpated_dar(self):
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dbgap_application = factories.dbGaPApplicationFactory.create()
#         # Create an old snapshot where the DAR was approved and a new one where it was closed.
#         old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__dbgap_application=dbgap_application,
#             dbgap_data_access_snapshot__is_most_recent=False,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
#             dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
#         )
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             dbgap_dar_id=old_dar.dbgap_dar_id,
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__dbgap_application=dbgap_application,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
#             dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
#         )
#         # Add the anvil group to the auth group for the workspace.
#         GroupGroupMembershipFactory.create(
#             parent_group=auth_domain,
#             child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(
#             dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 1)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.needs_action[0]
#         self.assertIsInstance(record, audit.RemoveAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.PREVIOUS_APPROVAL
#         )
#
#     def test_error_remove_access_unknown_reason(self):
#         """Access needs to be removed for an unknown reason."""
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         # Create an old snapshot where the DAR was rejected and a new one where it is still rejected.
#         old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
#             dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
#         )
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             dbgap_dar_id=old_dar.dbgap_dar_id,
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
#             dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
#         )
#         # Add the anvil group to the auth group for the workspace.
#         GroupGroupMembershipFactory.create(
#             parent_group=auth_domain,
#             child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(
#             dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 1)
#         record = dbgap_audit.errors[0]
#         self.assertIsInstance(record, audit.RemoveAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.ERROR_HAS_ACCESS
#         )
#
#     def test_error_remove_access_no_snapshot(self):
#         """Access needs to be removed for an unknown reason when there is no snapshot."""
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dbgap_application = factories.dbGaPApplicationFactory.create()
#         # Add the anvil group to the auth group for the workspace.
#         GroupGroupMembershipFactory.create(
#             parent_group=auth_domain,
#             child_group=dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(dbgap_application)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 1)
#         record = dbgap_audit.errors[0]
#         self.assertIsInstance(record, audit.RemoveAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(record.dbgap_application, dbgap_application)
#         self.assertIsNone(record.data_access_request)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.ERROR_HAS_ACCESS
#         )
#
#     def test_error_remove_access_snapshot_no_dar(self):
#         """Group has access but there is no matching DAR."""
#         # Create a workspace but no matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         # Add the anvil group to the auth group for the workspace.
#         snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
#         GroupGroupMembershipFactory.create(
#             parent_group=auth_domain,
#             child_group=snapshot.dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(snapshot.dbgap_application)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 1)
#         record = dbgap_audit.errors[0]
#         self.assertIsInstance(record, audit.RemoveAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(record.dbgap_application, snapshot.dbgap_application)
#         self.assertIsNone(record.data_access_request)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.ERROR_HAS_ACCESS
#         )
#
#     def test_approved_dar_for_different_application(self):
#         """There is an approved dar for a different application, but not this one."""
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         # Create an approved DAR from an unrelated application.
#         factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace
#         )
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
#         )
#         dbgap_audit = audit.dbGaPApplicationAccessAudit(
#             dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 1)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedNoAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.DAR_NOT_APPROVED
#         )
#
#
# class CDSAWorkspaceAccessAuditTest(TestCase):
#     """Tests for the CDSAWorkspaceAccessAudit class."""
#
#     def test_completed(self):
#         """completed is updated properly."""
#         workspace = factories.CDSAWorkspaceFactory.create()
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(workspace)
#         self.assertFalse(dbgap_audit.completed)
#         dbgap_audit.run_audit()
#         self.assertTrue(dbgap_audit.completed)
#
#     def test_no_applications_no_snapshots(self):
#         """run_audit with no existing workspaces and no snapshots."""
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#
#     def test_one_application_no_snapshots(self):
#         """run_audit with no existing workspaces and no snapshots."""
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dbgap_application = factories.dbGaPApplicationFactory.create()
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 1)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedNoAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(record.dbgap_application, dbgap_application)
#         self.assertIsNone(record.data_access_request)
#         self.assertEqual(record.note, audit.dbGaPAccessAudit.NO_SNAPSHOTS)
#
#     def test_snapshot_has_no_dars(self):
#         """run_audit with one snapshot that has no dars."""
#         # Create a workspace and a snapshot.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 1)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedNoAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(record.dbgap_application, dbgap_snapshot.dbgap_application)
#         self.assertIsNone(record.data_access_request)
#         self.assertEqual(record.note, audit.dbGaPAccessAudit.NO_DAR)
#
#     def test_one_verified_access(self):
#         """run_audit with one workspace that has verified access."""
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace
#         )
#         # Add the anvil group to the auth group for the workspace.
#         GroupGroupMembershipFactory(
#             parent_group=auth_domain,
#             child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 1)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#
#     def test_two_verified_access(self):
#         """run_audit with two applications that have verified access."""
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         # Create two applications and matching DARs.
#         dbgap_snapshot_1 = factories.dbGaPDataAccessSnapshotFactory.create()
#         dbgap_snapshot_2 = factories.dbGaPDataAccessSnapshotFactory.create()
#         dar_1 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace, dbgap_data_access_snapshot=dbgap_snapshot_1
#         )
#         dar_2 = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace, dbgap_data_access_snapshot=dbgap_snapshot_2
#         )
#         # Add the anvil group to the auth groups for the workspaces.
#         GroupGroupMembershipFactory(
#             parent_group=auth_domain,
#             child_group=dbgap_snapshot_1.dbgap_application.anvil_access_group,
#         )
#         GroupGroupMembershipFactory(
#             parent_group=auth_domain,
#             child_group=dbgap_snapshot_2.dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 2)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar_1.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar_1)
#         record = dbgap_audit.verified[1]
#         self.assertIsInstance(record, audit.VerifiedAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar_2.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar_2)
#
#     def test_one_verified_no_access_dar_not_approved(self):
#         """run_audit with one application that has verified no access."""
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
#         )
#         # Do not add the anvil group to the auth group for the workspace.
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 1)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedNoAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.DAR_NOT_APPROVED
#         )
#
#     def test_grant_access_new_approved_dar(self):
#         # Create a workspace and matching DAR.
#         # Workspace was created before the snapshot.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create(
#             created=timezone.now() - timedelta(weeks=3)
#         )
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
#         )
#         # Do not add the anvil group to the auth group for the workspace.
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 1)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.needs_action[0]
#         self.assertIsInstance(record, audit.GrantAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.NEW_APPROVED_DAR
#         )
#
#     def test_grant_access_new_workspace(self):
#         # Create a workspace and matching DAR.
#         # Workspace was created after the snapshot.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create(
#             created=timezone.now() - timedelta(weeks=2)
#         )
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
#         )
#         # Do not add the anvil group to the auth group for the workspace.
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 1)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.needs_action[0]
#         self.assertIsInstance(record, audit.GrantAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(record.note, audit.dbGaPApplicationAccessAudit.NEW_WORKSPACE)
#
#     def test_grant_access_updated_dar(self):
#         # Create a workspace and matching DAR.
#         # Workspace was created before the snapshot.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create(
#             created=timezone.now() - timedelta(weeks=4)
#         )
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dbgap_application = factories.dbGaPApplicationFactory.create()
#         # Create an old snapshot where the DAR was not approved.
#         old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__is_most_recent=False,
#             dbgap_data_access_snapshot__dbgap_application=dbgap_application,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
#             dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
#         )
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             dbgap_dar_id=old_dar.dbgap_dar_id,
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__dbgap_application=dbgap_application,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
#         )
#         # Do not add the anvil group to the auth group for the workspace.
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 1)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.needs_action[0]
#         self.assertIsInstance(record, audit.GrantAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.NEW_APPROVED_DAR
#         )
#
#     def test_remove_access_udpated_dar(self):
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dbgap_application = factories.dbGaPApplicationFactory.create()
#         # Create an old snapshot where the DAR was approved and a new one where it was closed.
#         old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__dbgap_application=dbgap_application,
#             dbgap_data_access_snapshot__is_most_recent=False,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
#             dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
#         )
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             dbgap_dar_id=old_dar.dbgap_dar_id,
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__dbgap_application=dbgap_application,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
#             dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
#         )
#         # Add the anvil group to the auth group for the workspace.
#         GroupGroupMembershipFactory.create(
#             parent_group=auth_domain,
#             child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 1)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.needs_action[0]
#         self.assertIsInstance(record, audit.RemoveAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.PREVIOUS_APPROVAL
#         )
#
#     def test_error_remove_access_unknown_reason(self):
#         """Access needs to be removed for an unknown reason."""
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dbgap_application = factories.dbGaPApplicationFactory.create()
#         # Create an old snapshot where the DAR was rejected and a new one where it is still rejected.
#         old_dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__dbgap_application=dbgap_application,
#             dbgap_data_access_snapshot__is_most_recent=False,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=3),
#             dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
#         )
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             dbgap_dar_id=old_dar.dbgap_dar_id,
#             cdsa_workspace=cdsa_workspace,
#             dbgap_data_access_snapshot__dbgap_application=dbgap_application,
#             dbgap_data_access_snapshot__created=timezone.now() - timedelta(weeks=2),
#             dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
#         )
#         # Add the anvil group to the auth group for the workspace.
#         GroupGroupMembershipFactory.create(
#             parent_group=auth_domain,
#             child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 1)
#         record = dbgap_audit.errors[0]
#         self.assertIsInstance(record, audit.RemoveAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.ERROR_HAS_ACCESS
#         )
#
#     def test_error_remove_access_no_snapshot(self):
#         """Access needs to be removed for an unknown reason when there is no snapshot."""
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         dbgap_application = factories.dbGaPApplicationFactory.create()
#         # Add the anvil group to the auth group for the workspace.
#         GroupGroupMembershipFactory.create(
#             parent_group=auth_domain,
#             child_group=dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 1)
#         record = dbgap_audit.errors[0]
#         self.assertIsInstance(record, audit.RemoveAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(record.dbgap_application, dbgap_application)
#         self.assertIsNone(record.data_access_request)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.ERROR_HAS_ACCESS
#         )
#
#     def test_error_remove_access_snapshot_no_dar(self):
#         """Group has access but there is no matching DAR."""
#         # Create a workspace but no matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         # Add the anvil group to the auth group for the workspace.
#         snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
#         GroupGroupMembershipFactory.create(
#             parent_group=auth_domain,
#             child_group=snapshot.dbgap_application.anvil_access_group,
#         )
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 0)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 1)
#         record = dbgap_audit.errors[0]
#         self.assertIsInstance(record, audit.RemoveAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(record.dbgap_application, snapshot.dbgap_application)
#         self.assertEqual(record.data_access_request, None)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.ERROR_HAS_ACCESS
#         )
#
#     def test_approved_dar_for_different_workspace(self):
#         """There is an approved dar for a different workspace, but not this one."""
#         # Create a workspace and matching DAR.
#         auth_domain = ManagedGroupFactory.create()
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace.workspace.authorization_domains.add(auth_domain)
#         # Create an unrelated workspace.
#         other_auth_domain = ManagedGroupFactory.create()
#         other_cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         other_cdsa_workspace.workspace.authorization_domains.add(other_auth_domain)
#         dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
#         # Create an approved DAR for the other workspace.
#         factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             cdsa_workspace=other_cdsa_workspace,
#             dbgap_data_access_snapshot=dbgap_snapshot,
#         )
#         # Create a rejected DAR for this workspace.
#         dar = factories.dbGaPDataAccessRequestForWorkspaceFactory.create(
#             dbgap_data_access_snapshot=dbgap_snapshot,
#             cdsa_workspace=cdsa_workspace,
#             dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
#         )
#         dbgap_audit = audit.CDSAWorkspaceAccessAudit(cdsa_workspace)
#         dbgap_audit.run_audit()
#         self.assertEqual(len(dbgap_audit.verified), 1)
#         self.assertEqual(len(dbgap_audit.needs_action), 0)
#         self.assertEqual(len(dbgap_audit.errors), 0)
#         record = dbgap_audit.verified[0]
#         self.assertIsInstance(record, audit.VerifiedNoAccess)
#         self.assertEqual(record.workspace, cdsa_workspace)
#         self.assertEqual(
#             record.dbgap_application, dar.dbgap_data_access_snapshot.dbgap_application
#         )
#         self.assertEqual(record.data_access_request, dar)
#         self.assertEqual(
#             record.note, audit.dbGaPApplicationAccessAudit.DAR_NOT_APPROVED
#         )
#
#
# class dbGaPAccessAuditTableTest(TestCase):
#     """Tests for the `dbGaPAccessAuditTableTest` table."""
#
#     def test_no_rows(self):
#         """Table works with no rows."""
#         table = audit.dbGaPAccessAuditTable([])
#         self.assertIsInstance(table, audit.dbGaPAccessAuditTable)
#         self.assertEqual(len(table.rows), 0)
#
#     def test_one_row(self):
#         """Table works with one row."""
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         data = [
#             {
#                 "workspace": cdsa_workspace,
#                 "data_access_request": factories.dbGaPDataAccessRequestForWorkspaceFactory(
#                     cdsa_workspace=cdsa_workspace
#                 ),
#                 "note": "a note",
#                 "action": "",
#                 "action_url": "",
#             }
#         ]
#         table = audit.dbGaPAccessAuditTable(data)
#         self.assertIsInstance(table, audit.dbGaPAccessAuditTable)
#         self.assertEqual(len(table.rows), 1)
#
#     def test_two_rows(self):
#         """Table works with two rows."""
#         cdsa_workspace_1 = factories.CDSAWorkspaceFactory.create()
#         cdsa_workspace_2 = factories.CDSAWorkspaceFactory.create()
#         data = [
#             {
#                 "workspace": cdsa_workspace_1,
#                 "data_access_request": factories.dbGaPDataAccessRequestForWorkspaceFactory(
#                     cdsa_workspace=cdsa_workspace_1
#                 ),
#                 "note": "a note",
#                 "action": "",
#                 "action_url": "",
#             },
#             {
#                 "workspace": cdsa_workspace_2,
#                 "data_access_request": factories.dbGaPDataAccessRequestForWorkspaceFactory(
#                     cdsa_workspace=cdsa_workspace_2
#                 ),
#                 "note": "a note",
#                 "action": "",
#                 "action_url": "",
#             },
#         ]
#         table = audit.dbGaPAccessAuditTable(data)
#         self.assertIsInstance(table, audit.dbGaPAccessAuditTable)
#         self.assertEqual(len(table.rows), 2)
#
#     def test_render_action(self):
#         """Render action works as expected for grant access types."""
#         cdsa_workspace = factories.CDSAWorkspaceFactory.create()
#         data = [
#             {
#                 "workspace": cdsa_workspace,
#                 "data_access_request": factories.dbGaPDataAccessRequestForWorkspaceFactory(
#                     cdsa_workspace=cdsa_workspace
#                 ),
#                 "note": "a note",
#                 "action": "Grant",
#                 "action_url": "foo",
#             }
#         ]
#         table = audit.dbGaPAccessAuditTable(data)
#         self.assertIsInstance(table, audit.dbGaPAccessAuditTable)
#         self.assertEqual(len(table.rows), 1)
#         self.assertIn("foo", table.rows[0].get_cell("action"))
#         self.assertIn("Grant", table.rows[0].get_cell("action"))
