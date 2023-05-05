# from datetime import timedelta

from anvil_consortium_manager.tests.factories import (
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
)
from django.conf import settings
from django.test import TestCase, override_settings

from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory

from ..audit import signed_agreement_audit, workspace_audit
from . import factories

# from django.utils import timezone


class SignedAgreementAuditResultTest(TestCase):
    """General tests of the AuditResult dataclasses for SignedAgreements."""

    def setUp(self):
        super().setUp()
        self.cdsa_group = ManagedGroupFactory.create(
            name=settings.ANVIL_CDSA_GROUP_NAME
        )

    def test_verified_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        signed_agreement_audit.VerifiedAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )

    def test_verified_no_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        signed_agreement_audit.VerifiedNoAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )

    def test_grant_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.GrantAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        instance.get_action_url()

    def test_remove_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.RemoveAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        instance.get_action_url()

    def test_remove_access_no_dar(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.RemoveAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        instance.get_action_url()

    def test_error(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.OtherError(
            signed_agreement=signed_agreement,
            note="foo",
        )
        instance.get_action_url()

    def test_anvil_group_name(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.VerifiedAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        self.assertEqual(instance.anvil_cdsa_group, self.cdsa_group)

    @override_settings(ANVIL_CDSA_GROUP_NAME="FOO")
    def test_anvil_group_name_setting(self):
        group = ManagedGroupFactory.create(name="FOO")
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.VerifiedAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        self.assertEqual(instance.anvil_cdsa_group, group)


class AccessAuditResultTest(TestCase):
    """Tests for the AccessAuditResult class."""

    def setUp(self):
        super().setUp()
        self.cdsa_group = ManagedGroupFactory.create(
            name=settings.ANVIL_CDSA_GROUP_NAME
        )

    def test_completed(self):
        """completed is updated properly."""
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        self.assertFalse(cdsa_audit.completed)
        cdsa_audit.run_audit()
        self.assertTrue(cdsa_audit.completed)

    def test_no_signed_agreements(self):
        """Audit works when there are no signed agreements."""
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        self.assertFalse(cdsa_audit.completed)
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_signed_agreement_primary_verified_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 1)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.note, cdsa_audit.VALID_CDSA)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_signed_agreement_primary_needs_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        # Do not add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group, child_group=signed_agreement.anvil_access_group
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.note, cdsa_audit.VALID_CDSA)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_signed_agreement_member_component_verified_access(self):
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(study_site=study_site)
        component_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False, study_site=study_site
        )
        # Add the component agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=component_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(component_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, component_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.VALID_CDSA)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_signed_agreement_member_component_no_primary_no_access(self):
        component_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        # Do not add the component agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=component_agreement.signed_agreement.anvil_access_group
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(component_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, component_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_CDSA)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_signed_agreement_member_component_needs_access(self):
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(study_site=study_site)
        component_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False, study_site=study_site
        )
        # Do not add the component agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=component_agreement.signed_agreement.anvil_access_group
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(component_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, component_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.VALID_CDSA)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_signed_agreement_member_component_needs_error(self):
        # No primary, but the agreement has access (incorrectly).
        component_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        # Add the component agreement access group to the CDSA group (to trip the error).
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=component_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(component_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, component_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_CDSA)

    def test_one_signed_agreement_data_affiliate_component_verified_access(self):
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        component_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False, study=study
        )
        # Add the component agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=component_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(component_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, component_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.VALID_CDSA)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_signed_agreement_data_affiliate_component_no_primary_no_access(self):
        component_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        # Do not add the component agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=component_agreement.signed_agreement.anvil_access_group
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(component_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, component_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_CDSA)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_signed_agreement_data_affiliate_component_needs_access(self):
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        component_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False, study=study
        )
        # Do not add the component agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=component_agreement.signed_agreement.anvil_access_group
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(component_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, component_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.VALID_CDSA)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_signed_agreement_data_affiliate_component_needs_error(self):
        # No primary, but the agreement has access (incorrectly).
        component_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        # Add the component agreement access group to the CDSA group (to trip the error).
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=component_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(component_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, component_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_CDSA)

    def test_one_signed_agreement_nondataaffiliate_component(self):
        factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        with self.assertRaises(RuntimeError):
            cdsa_audit.run_audit()

    def test_other_error(self):
        signed_agreement = factories.SignedAgreementFactory.create(
            is_primary=False, type="MEMBER"
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, signed_agreement_audit.OtherError)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ERROR_OTHER_CASE)


class SignedAgreementAccessAuditTableTest(TestCase):
    """Tests for the `SignedAgreementAccessAuditTable` table."""

    def test_no_rows(self):
        """Table works with no rows."""
        table = signed_agreement_audit.SignedAgreementAccessAuditTable([])
        self.assertIsInstance(
            table, signed_agreement_audit.SignedAgreementAccessAuditTable
        )
        self.assertEqual(len(table.rows), 0)

    def test_one_row(self):
        """Table works with one row."""
        signed_agreement = factories.SignedAgreementFactory.create()
        data = [
            {
                "signed_agreement": signed_agreement,
                "agreement_type": "Foo",
                "agreement_group": "Bar",
                "note": "a note",
                "action": "",
                "action_url": "",
            }
        ]
        table = signed_agreement_audit.SignedAgreementAccessAuditTable(data)
        self.assertIsInstance(
            table, signed_agreement_audit.SignedAgreementAccessAuditTable
        )
        self.assertEqual(len(table.rows), 1)

    def test_two_rows(self):
        """Table works with two rows."""
        signed_agreement_1 = factories.SignedAgreementFactory.create()
        signed_agreement_2 = factories.SignedAgreementFactory.create()
        data = [
            {
                "signed_agreement": signed_agreement_1,
                "agreement_type": "Foo",
                "agreement_group": "Bar",
                "note": "a note",
                "action": "",
                "action_url": "",
            },
            {
                "signed_agreement": signed_agreement_2,
                "agreement_type": "Foo",
                "agreement_group": "Bar",
                "note": "a note",
                "action": "",
                "action_url": "",
            },
        ]
        table = signed_agreement_audit.SignedAgreementAccessAuditTable(data)
        self.assertIsInstance(
            table, signed_agreement_audit.SignedAgreementAccessAuditTable
        )
        self.assertEqual(len(table.rows), 2)

    def test_render_action(self):
        """Render action works as expected for grant access types."""
        signed_agreement = factories.SignedAgreementFactory.create()
        data = [
            {
                "signed_agreement": signed_agreement,
                "agreement_type": "Foo",
                "agreement_group": "Bar",
                "note": "a note",
                "action": "Grant",
                "action_url": "foo",
            }
        ]
        table = signed_agreement_audit.SignedAgreementAccessAuditTable(data)
        self.assertIsInstance(
            table, signed_agreement_audit.SignedAgreementAccessAuditTable
        )
        self.assertEqual(len(table.rows), 1)
        self.assertIn("foo", table.rows[0].get_cell("action"))
        self.assertIn("Grant", table.rows[0].get_cell("action"))


class WorkspaceAuditResultTest(TestCase):
    """General tests of the AuditResult dataclasses for workspaces."""

    def setUp(self):
        super().setUp()
        self.cdsa_group = ManagedGroupFactory.create(
            name=settings.ANVIL_CDSA_GROUP_NAME
        )
        self.study = StudyFactory.create()

    def test_verified_access(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=self.study
        )
        workspace_audit.VerifiedAccess(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )

    def test_verified_no_access(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=self.study
        )
        workspace_audit.VerifiedNoAccess(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )

    def test_grant_access(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=self.study
        )
        instance = workspace_audit.GrantAccess(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        instance.get_action_url()

    def test_remove_access(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=self.study
        )
        instance = workspace_audit.RemoveAccess(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        instance.get_action_url()

    def test_error(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=self.study
        )
        instance = workspace_audit.OtherError(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        instance.get_action_url()

    def test_error_no_data_affiliate_agreement(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        instance = workspace_audit.OtherError(
            workspace=workspace,
            note="foo",
        )
        instance.get_action_url()

    def test_anvil_group_name(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=self.study
        )
        instance = workspace_audit.OtherError(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        self.assertEqual(instance.anvil_cdsa_group, self.cdsa_group)

    @override_settings(ANVIL_CDSA_GROUP_NAME="FOO")
    def test_anvil_group_name_setting(self):
        group = ManagedGroupFactory.create(name="FOO")
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=self.study
        )
        instance = workspace_audit.OtherError(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        self.assertEqual(instance.anvil_cdsa_group, group)


class WorkspaceAccessAuditTest(TestCase):
    """Tests for the WorkspaceAccessAudit class."""

    def setUp(self):
        super().setUp()
        self.cdsa_group = ManagedGroupFactory.create(
            name=settings.ANVIL_CDSA_GROUP_NAME
        )

    def test_completed(self):
        """completed is updated properly."""
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        self.assertFalse(cdsa_audit.completed)
        cdsa_audit.run_audit()
        self.assertTrue(cdsa_audit.completed)

    def test_no_workspaces(self):
        """Audit works when there are no workspaces."""
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        self.assertFalse(cdsa_audit.completed)
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_workspace_with_primary_verified_access(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study
        )
        # Add the CDSA group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 1)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.VALID_CDSA)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_workspace_no_primary_no_verified_access(self):
        workspace = factories.CDSAWorkspaceFactory.create()
        # Do not CDSA group to the auth domain.
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=self.cdsa_group,
        # )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 1)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedNoAccess)
        self.assertIsNone(record.data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_CDSA)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_one_workspace_no_primary_error_has_access(self):
        workspace = factories.CDSAWorkspaceFactory.create()
        # Add the CDSA group to the auth domain - this is an error.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, workspace_audit.RemoveAccess)
        self.assertIsNone(record.data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_CDSA)

    def test_one_workspace_with_primary_no_access(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study
        )
        # Do not add the CDSA group to the auth domain.
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=self.cdsa_group,
        # )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, workspace_audit.GrantAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.VALID_CDSA)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_ignores_component_agreement(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        factories.DataAffiliateAgreementFactory.create(
            study=study, signed_agreement__is_primary=False
        )
        # Do not add the CDSA group to the auth domain.
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=self.cdsa_group,
        # )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 1)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedNoAccess)
        self.assertIsNone(record.data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_CDSA)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_two_workspaces(self):
        study = StudyFactory.create()
        workspace_1 = factories.CDSAWorkspaceFactory.create(study=study)
        workspace_2 = factories.CDSAWorkspaceFactory.create(study=study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study
        )
        # Add the CDSA group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=workspace_1.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        GroupGroupMembershipFactory.create(
            parent_group=workspace_2.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 2)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace_1)
        self.assertEqual(record.note, cdsa_audit.VALID_CDSA)
        record = cdsa_audit.verified[1]
        self.assertIsInstance(record, workspace_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace_2)
        self.assertEqual(record.note, cdsa_audit.VALID_CDSA)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    # def test_other_error(self):
    #     signed_agreement = factories.SignedAgreementFactory.create(
    #         is_primary=False, type="MEMBER"
    #     )
    #     cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
    #     cdsa_audit._audit_signed_agreement(signed_agreement)
    #     self.assertEqual(len(cdsa_audit.verified), 0)
    #     self.assertEqual(len(cdsa_audit.needs_action), 0)
    #     self.assertEqual(len(cdsa_audit.errors), 1)
    #     record = cdsa_audit.errors[0]
    #     self.assertIsInstance(record, signed_agreement_audit.OtherError)
    #     self.assertEqual(record.signed_agreement, signed_agreement)
    #     self.assertEqual(record.note, cdsa_audit.ERROR_OTHER_CASE)


class WorkspaceAccessAuditTableTest(TestCase):
    """Tests for the `WorkspaceAccessAuditTable` table."""

    def test_no_rows(self):
        """Table works with no rows."""
        table = workspace_audit.WorkspaceAccessAuditTable([])
        self.assertIsInstance(table, workspace_audit.WorkspaceAccessAuditTable)
        self.assertEqual(len(table.rows), 0)

    def test_one_row(self):
        """Table works with one row."""
        study = StudyFactory.create()
        agreement = factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        data = [
            {
                "data_affiliate_agreement": agreement,
                "workspace": workspace,
                "note": "a note",
                "action": "",
                "action_url": "",
            }
        ]
        table = workspace_audit.WorkspaceAccessAuditTable(data)
        self.assertEqual(len(table.rows), 1)

    def test_two_rows(self):
        """Table works with two rows."""
        study_1 = StudyFactory.create()
        agreement_1 = factories.DataAffiliateAgreementFactory.create(study=study_1)
        workspace_1 = factories.CDSAWorkspaceFactory.create(study=study_1)
        study_2 = StudyFactory.create()
        agreement_2 = factories.DataAffiliateAgreementFactory.create(study=study_2)
        workspace_2 = factories.CDSAWorkspaceFactory.create(study=study_2)
        data = [
            {
                "data_affiliate_agreement": agreement_1,
                "workspace": workspace_1,
                "note": "a note",
                "action": "",
                "action_url": "",
            },
            {
                "data_affiliate_agreement": agreement_2,
                "workspace": workspace_2,
                "note": "a note",
                "action": "",
                "action_url": "",
            },
        ]
        table = workspace_audit.WorkspaceAccessAuditTable(data)
        self.assertEqual(len(table.rows), 2)

    def test_render_action(self):
        """Render action works as expected for grant access types."""
        study = StudyFactory.create()
        agreement = factories.DataAffiliateAgreementFactory.create(study=study)
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        data = [
            {
                "data_affiliate_agreement": agreement,
                "workspace": workspace,
                "note": "a note",
                "action": "Grant",
                "action_url": "foo",
            }
        ]
        table = workspace_audit.WorkspaceAccessAuditTable(data)
        self.assertEqual(len(table.rows), 1)
        self.assertIn("foo", table.rows[0].get_cell("action"))
        self.assertIn("Grant", table.rows[0].get_cell("action"))
