# from datetime import timedelta

from anvil_consortium_manager.tests.factories import (
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
)
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory

from .. import models
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
        instance = signed_agreement_audit.VerifiedAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        self.assertIsNone(instance.action)
        self.assertEqual(
            instance.get_action_url(),
            reverse(
                "cdsa:signed_agreements:audit:resolve", args=[signed_agreement.cc_id]
            ),
        )

    def test_verified_no_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.VerifiedNoAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        self.assertIsNone(instance.action)
        self.assertEqual(
            instance.get_action_url(),
            reverse(
                "cdsa:signed_agreements:audit:resolve", args=[signed_agreement.cc_id]
            ),
        )

    def test_grant_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.GrantAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        self.assertEqual(instance.action, "Grant access")
        self.assertEqual(
            instance.get_action_url(),
            reverse(
                "cdsa:signed_agreements:audit:resolve", args=[signed_agreement.cc_id]
            ),
        )

    def test_remove_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.RemoveAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        self.assertEqual(instance.action, "Remove access")
        self.assertEqual(
            instance.get_action_url(),
            reverse(
                "cdsa:signed_agreements:audit:resolve", args=[signed_agreement.cc_id]
            ),
        )

    def test_error(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.OtherError(
            signed_agreement=signed_agreement,
            note="foo",
        )
        self.assertEqual(
            instance.get_action_url(),
            reverse(
                "cdsa:signed_agreements:audit:resolve", args=[signed_agreement.cc_id]
            ),
        )

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


class SignedAgreementAccessAuditTest(TestCase):
    """Tests for the SignedAgreementAccessAudit class."""

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

    def test_one_signed_agreement(self):
        """Audit works when there is one signed agreement."""
        this_agreement = factories.MemberAgreementFactory.create()
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_two_signed_agreements(self):
        """Audit runs on all signed agreements by default."""
        # Create two signed agreements that need to be added to the SAG group.
        factories.MemberAgreementFactory.create_batch(2)
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.needs_action), 2)

    def test_signed_agreement_queryset(self):
        """Audit only runs on SignedAgreements in the signed_agreement_queryset."""
        this_agreement = factories.MemberAgreementFactory.create()
        factories.MemberAgreementFactory.create()
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit(
            signed_agreement_queryset=models.SignedAgreement.objects.filter(
                pk=this_agreement.signed_agreement.pk
            )
        )
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_dbgap_application_queryset_wrong_class(self):
        """dbGaPAccessAudit raises error if dbgap_application_queryset has the wrong model class."""
        with self.assertRaises(ValueError) as e:
            signed_agreement_audit.SignedAgreementAccessAudit(
                signed_agreement_queryset=models.MemberAgreement.objects.all()
            )
        self.assertEqual(
            str(e.exception),
            "signed_agreement_queryset must be a queryset of SignedAgreement objects.",
        )

    def test_dbgap_application_queryset_not_queryset(self):
        """dbGaPAccessAudit raises error if dbgap_application_queryset is not a queryset."""
        member_agreement = factories.MemberAgreementFactory.create()
        with self.assertRaises(ValueError) as e:
            signed_agreement_audit.SignedAgreementAccessAudit(
                signed_agreement_queryset=member_agreement.signed_agreement
            )
        self.assertEqual(
            str(e.exception),
            "signed_agreement_queryset must be a queryset of SignedAgreement objects.",
        )

    def test_member_primary_in_group(self):
        """Member primary agreement with valid version in CDSA group."""
        this_agreement = factories.MemberAgreementFactory.create()
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_member_primary_not_in_group(self):
        """Member primary agreement with valid version not in CDSA group."""
        this_agreement = factories.MemberAgreementFactory.create()
        # Do not add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_member_primary_invalid_version_in_group(self):
        """Member primary agreement, active, with invalid version in CDSA group."""
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__version__major_version__is_valid=False
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_member_primary_invalid_version_not_in_group(self):
        """Member primary agreement, with invalid version, not in CDSA group."""
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__version__major_version__is_valid=False
        )
        # Do not add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_member_primary_valid_not_active_in_group(self):
        """Member primary agreement with valid version but isn't active, in CDSA group."""
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_AGREEMENT)

    def test_member_primary_valid_not_active_not_in_group(self):
        """Member primary agreement with valid version but isn't active, not in CDSA group."""
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_AGREEMENT)

    def test_member_component_has_primary_in_group(self):
        """Member component agreement, with valid version, with primary with valid version, in CDSA group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(study_site=study_site)
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False, study_site=study_site
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_member_component_has_primary_not_in_group(self):
        """Member component agreement, with valid version, with primary with valid version, not in CDSA group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(study_site=study_site)
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False, study_site=study_site
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_member_component_inactive_has_primary_in_group(self):
        """Member component agreement, inactive, with valid version, with primary with valid version, in CDSA group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(study_site=study_site)
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False,
            study_site=study_site,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_AGREEMENT)

    def test_member_component_inactive_has_primary_not_in_group(self):
        """Member component agreement, inactive, with valid version, with valid active primary, not in CDSA group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(study_site=study_site)
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False,
            study_site=study_site,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_AGREEMENT)

    def test_member_component_has_primary_with_invalid_version_in_group(self):
        """Member component agreement, with valid version, with active primary with invalid version, in CDSA group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(
            study_site=study_site,
            signed_agreement__version__major_version__is_valid=False,
        )
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False, study_site=study_site
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_member_component_has_primary_with_invalid_version_not_in_group(self):
        """Member component agreement, with valid version, with active primary with invalid version, not in group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(
            study_site=study_site,
            signed_agreement__version__major_version__is_valid=False,
        )
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False, study_site=study_site
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_member_component_has_inactive_primary_in_group(self):
        """Member component agreement, with valid version, with inactive primary, in CDSA group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(
            study_site=study_site,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False, study_site=study_site
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.PRIMARY_NOT_ACTIVE)

    def test_member_component_has_inactive_primary_not_in_group(self):
        """Member component agreement, with valid version, with inactive primary, not in CDSA group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(
            study_site=study_site,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False, study_site=study_site
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.PRIMARY_NOT_ACTIVE)

    def test_member_component_no_primary_in_group(self):
        """Member component agreement, with valid version, with no primary, in CDSA group."""
        study_site = StudySiteFactory.create()
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False, study_site=study_site
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_member_component_no_primary_not_in_group(self):
        """Member component agreement, with valid version, with no primary, not in CDSA group."""
        study_site = StudySiteFactory.create()
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False, study_site=study_site
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_member_component_invalid_version_has_primary_in_group(self):
        """Member component agreement, with invalid version, with a valid primary, in CDSA group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(study_site=study_site)
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False,
            study_site=study_site,
            signed_agreement__version__major_version__is_valid=False,
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_member_component_invalid_version_has_primary_not_in_group(self):
        """Member component agreement, with invalid version, with a valid primary, not in CDSA group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(study_site=study_site)
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False,
            study_site=study_site,
            signed_agreement__version__major_version__is_valid=False,
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_member_component_invalid_version_has_primary_with_invalid_version_in_group(
        self,
    ):
        """Member component agreement, with invalid version, with an invalid primary, in CDSA group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(study_site=study_site)
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False,
            study_site=study_site,
            signed_agreement__version__major_version__is_valid=False,
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_member_component_invalid_version_has_primary_with_invalid_version_not_in_group(
        self,
    ):
        """Member component agreement, with invalid version, with an invalid primary, not in CDSA group."""
        study_site = StudySiteFactory.create()
        factories.MemberAgreementFactory.create(study_site=study_site)
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False,
            study_site=study_site,
            signed_agreement__version__major_version__is_valid=False,
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_member_component_invalid_version_no_primary_in_group(self):
        """Member component agreement, with invalid version, with no primary, in CDSA group."""
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False,
            signed_agreement__version__major_version__is_valid=False,
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_member_component_invalid_version_no_primary_not_in_group(self):
        """Member component agreement, with invalid version, with no primary, not in CDSA group."""
        this_agreement = factories.MemberAgreementFactory.create(
            signed_agreement__is_primary=False,
            signed_agreement__version__major_version__is_valid=False,
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_data_affiliate_primary_in_group(self):
        """Member primary agreement with valid version in CDSA group."""
        this_agreement = factories.DataAffiliateAgreementFactory.create()
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_data_affiliate_primary_not_in_group(self):
        """Member primary agreement with valid version not in CDSA group."""
        this_agreement = factories.DataAffiliateAgreementFactory.create()
        # Do not add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_data_affiliate_primary_invalid_version_in_group(self):
        """Member primary agreement, active, with invalid version in CDSA group."""
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__version__major_version__is_valid=False
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_data_affiliate_primary_invalid_version_not_in_group(self):
        """Member primary agreement, with invalid version, not in CDSA group."""
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__version__major_version__is_valid=False
        )
        # Do not add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_data_affiliate_primary_valid_not_active_in_group(self):
        """Member primary agreement with valid version but isn't active, in CDSA group."""
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_AGREEMENT)

    def test_data_affiliate_primary_valid_not_active_not_in_group(self):
        """Member primary agreement with valid version but isn't active, not in CDSA group."""
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_AGREEMENT)

    def test_data_affiliate_component_has_primary_in_group(self):
        """Member component agreement, with valid version, with primary with valid version, in CDSA group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False, study=study
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_data_affiliate_component_has_primary_not_in_group(self):
        """Member component agreement, with valid version, with primary with valid version, not in CDSA group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False, study=study
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_data_affiliate_component_inactive_has_primary_in_group(self):
        """Member component agreement, inactive, with valid version, with primary with valid version, in CDSA group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False,
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_AGREEMENT)

    def test_data_affiliate_component_inactive_has_primary_not_in_group(self):
        """Member component agreement, inactive, with valid version, with valid active primary, not in CDSA group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False,
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_AGREEMENT)

    def test_data_affiliate_component_has_primary_with_invalid_version_in_group(self):
        """Member component agreement, with valid version, with active primary with invalid version, in CDSA group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__version__major_version__is_valid=False,
        )
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False, study=study
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_data_affiliate_component_has_primary_with_invalid_version_not_in_group(
        self,
    ):
        """Member component agreement, with valid version, with active primary with invalid version, not in group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__version__major_version__is_valid=False,
        )
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False, study=study
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_data_affiliate_component_has_inactive_primary_in_group(self):
        """Member component agreement, with valid version, with inactive primary, in CDSA group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False, study=study
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.PRIMARY_NOT_ACTIVE)

    def test_data_affiliate_component_has_inactive_primary_not_in_group(self):
        """Member component agreement, with valid version, with inactive primary, not in CDSA group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False, study=study
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.PRIMARY_NOT_ACTIVE)

    def test_data_affiliate_component_no_primary_in_group(self):
        """Member component agreement, with valid version, with no primary, in CDSA group."""
        study = StudyFactory.create()
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False, study=study
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_data_affiliate_component_no_primary_not_in_group(self):
        """Member component agreement, with valid version, with no primary, not in CDSA group."""
        study = StudyFactory.create()
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False, study=study
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_data_affiliate_component_invalid_version_has_primary_in_group(self):
        """Member component agreement, with invalid version, with a valid primary, in CDSA group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False,
            study=study,
            signed_agreement__version__major_version__is_valid=False,
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_data_affiliate_component_invalid_version_has_primary_not_in_group(self):
        """Member component agreement, with invalid version, with a valid primary, not in CDSA group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False,
            study=study,
            signed_agreement__version__major_version__is_valid=False,
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_data_affiliate_component_invalid_version_has_primary_with_invalid_version_in_group(
        self,
    ):
        """Member component agreement, with invalid version, with an invalid primary, in CDSA group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False,
            study=study,
            signed_agreement__version__major_version__is_valid=False,
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_data_affiliate_component_invalid_version_has_primary_with_invalid_version_not_in_group(
        self,
    ):
        """Member component agreement, with invalid version, with an invalid primary, not in CDSA group."""
        study = StudyFactory.create()
        factories.DataAffiliateAgreementFactory.create(study=study)
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False,
            study=study,
            signed_agreement__version__major_version__is_valid=False,
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_COMPONENT_AGREEMENT)

    def test_data_affiliate_component_invalid_version_no_primary_in_group(self):
        """Member component agreement, with invalid version, with no primary, in CDSA group."""
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False,
            signed_agreement__version__major_version__is_valid=False,
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_data_affiliate_component_invalid_version_no_primary_not_in_group(self):
        """Member component agreement, with invalid version, with no primary, not in CDSA group."""
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False,
            signed_agreement__version__major_version__is_valid=False,
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_non_data_affiliate_primary_in_group(self):
        """Non data affiliate primary agreement with valid version in CDSA group."""
        this_agreement = factories.NonDataAffiliateAgreementFactory.create()
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_non_data_affiliate_primary_not_in_group(self):
        """Non data affiliate primary agreement with valid version not in CDSA group."""
        this_agreement = factories.NonDataAffiliateAgreementFactory.create()
        # Do not add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_non_data_affiliate_primary_invalid_version_in_group(self):
        """Non data affiliate primary agreement with invalid version in CDSA group."""
        this_agreement = factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__version__major_version__is_valid=False
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_non_data_affiliate_primary_invalid_version_not_in_group(self):
        """Non data affiliate primary agreement, with invalid version, not in CDSA group."""
        this_agreement = factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__version__major_version__is_valid=False
        )
        # Do not add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_non_data_affiliate_primary_valid_not_active_in_group(self):
        """Non Data affiliate primary agreement with valid version but isn't active, in CDSA group."""
        this_agreement = factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_AGREEMENT)

    def test_non_data_affiliate_primary_valid_not_active_not_in_group(self):
        """Non data affiliate primary agreement with valid version but isn't active, not in CDSA group."""
        this_agreement = factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN
        )
        # # Add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, signed_agreement_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_AGREEMENT)

    def test_non_data_affiliate_component_in_cdsa_group(self):
        """Non data affiliate component agreement."""
        this_agreement = factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        # Add the signed agreement access group to the CDSA group.
        GroupGroupMembershipFactory.create(
            parent_group=self.cdsa_group,
            child_group=this_agreement.signed_agreement.anvil_access_group,
        )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, signed_agreement_audit.OtherError)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ERROR_NON_DATA_AFFILIATE_COMPONENT)

    def test_non_data_affiliate_component_not_in_cdsa_group(self):
        """Non data affiliate component agreement."""
        this_agreement = factories.NonDataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=False
        )
        # Do not add the signed agreement access group to the CDSA group.
        # GroupGroupMembershipFactory.create(
        #     parent_group=self.cdsa_group,
        #     child_group=this_agreement.signed_agreement.anvil_access_group,
        # )
        cdsa_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        cdsa_audit._audit_signed_agreement(this_agreement.signed_agreement)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, signed_agreement_audit.OtherError)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ERROR_NON_DATA_AFFILIATE_COMPONENT)


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
        member_agreement = factories.MemberAgreementFactory.create()
        data = [
            {
                "signed_agreement": member_agreement.signed_agreement,
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
        self.assertIn(
            str(member_agreement.signed_agreement.cc_id),
            table.rows[0].get_cell("signed_agreement"),
        )
        self.assertEqual(table.rows[0].get_cell("note"), "a note")

    def test_two_rows(self):
        """Table works with two rows."""
        signed_agreement_1 = factories.MemberAgreementFactory.create()
        signed_agreement_2 = factories.DataAffiliateAgreementFactory.create()
        data = [
            {
                "signed_agreement": signed_agreement_1.signed_agreement,
                "agreement_type": "Foo",
                "agreement_group": "Bar",
                "note": "note 1",
                "action": "",
                "action_url": "",
            },
            {
                "signed_agreement": signed_agreement_2.signed_agreement,
                "agreement_type": "Foo",
                "agreement_group": "Bar",
                "note": "note 2",
                "action": "",
                "action_url": "",
            },
        ]
        table = signed_agreement_audit.SignedAgreementAccessAuditTable(data)
        self.assertIsInstance(
            table, signed_agreement_audit.SignedAgreementAccessAuditTable
        )
        self.assertEqual(len(table.rows), 2)
        self.assertIn(
            str(signed_agreement_1.signed_agreement.cc_id),
            table.rows[0].get_cell("signed_agreement"),
        )
        self.assertEqual(table.rows[0].get_cell("note"), "note 1")
        self.assertIn(
            str(signed_agreement_2.signed_agreement.cc_id),
            table.rows[1].get_cell("signed_agreement"),
        )
        self.assertEqual(table.rows[1].get_cell("note"), "note 2")


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
        instance = workspace_audit.VerifiedAccess(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        self.assertIsNone(instance.get_action_url())

    def test_verified_no_access(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=self.study
        )
        instance = workspace_audit.VerifiedNoAccess(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        self.assertIsNone(instance.get_action_url())

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
        expected_url = reverse(
            "anvil_consortium_manager:managed_groups:member_groups:new_by_child",
            args=[workspace.workspace.authorization_domains.first(), self.cdsa_group],
        )
        self.assertEqual(instance.get_action_url(), expected_url)

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
        expected_url = reverse(
            "anvil_consortium_manager:managed_groups:member_groups:delete",
            args=[workspace.workspace.authorization_domains.first(), self.cdsa_group],
        )
        self.assertEqual(instance.get_action_url(), expected_url)

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
        self.assertIsNone(instance.get_action_url())

    def test_error_no_data_affiliate_agreement(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        instance = workspace_audit.OtherError(
            workspace=workspace,
            note="foo",
        )
        self.assertIsNone(instance.get_action_url())

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

    def test_cdsa_workspace_queryset(self):
        """Audit only runs on CDSAWorkspaces in the cdsa_workspace_queryset."""
        cdsa_workspace = factories.CDSAWorkspaceFactory.create()
        factories.CDSAWorkspaceFactory.create()
        cdsa_audit = workspace_audit.WorkspaceAccessAudit(
            cdsa_workspace_queryset=models.CDSAWorkspace.objects.filter(
                pk=cdsa_workspace.workspace.pk
            )
        )
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedNoAccess)
        self.assertEqual(record.workspace, cdsa_workspace)
        self.assertIsNone(record.data_affiliate_agreement)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_cdsa_workspace_queryset_wrong_class(self):
        """Audit raises error if dbgap_application_queryset has the wrong model class."""
        with self.assertRaises(ValueError) as e:
            workspace_audit.WorkspaceAccessAudit(
                cdsa_workspace_queryset=models.SignedAgreement.objects.all()
            )
        self.assertEqual(
            str(e.exception),
            "cdsa_workspace_queryset must be a queryset of CDSAWorkspace objects.",
        )

    def test_cdsa_workspace_queryset_not_queryset(self):
        """Audit raises error if dbgap_application_queryset is not a queryset."""
        workspace = factories.CDSAWorkspaceFactory.create()
        with self.assertRaises(ValueError) as e:
            workspace_audit.WorkspaceAccessAudit(cdsa_workspace_queryset=workspace)
        self.assertEqual(
            str(e.exception),
            "cdsa_workspace_queryset must be a queryset of CDSAWorkspace objects.",
        )

    def test_primary_in_auth_domain(self):
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
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_primary_not_in_auth_domain(self):
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
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, workspace_audit.GrantAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_no_primary_not_in_auth_domain(self):
        workspace = factories.CDSAWorkspaceFactory.create()
        # Do not CDSA group to the auth domain.
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=self.cdsa_group,
        # )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedNoAccess)
        self.assertIsNone(record.data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_no_primary_in_auth_domain(self):
        workspace = factories.CDSAWorkspaceFactory.create()
        # Add the CDSA group to the auth domain - this is an error.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, workspace_audit.RemoveAccess)
        self.assertIsNone(record.data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_primary_invalid_version_not_in_auth_domain(self):
        workspace = factories.CDSAWorkspaceFactory.create()
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__version__major_version__is_valid=False,
            study=workspace.study,
        )
        # Do not add the CDSA group to the auth domain.
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=self.cdsa_group,
        # )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, workspace_audit.GrantAccess)
        self.assertEqual(record.data_affiliate_agreement, this_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_primary_invalid_version_in_auth_domain(self):
        workspace = factories.CDSAWorkspaceFactory.create()
        this_agreement = factories.DataAffiliateAgreementFactory.create(
            signed_agreement__version__major_version__is_valid=False,
            study=workspace.study,
        )
        # Add the CDSA group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, this_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_primary_inactive_not_in_auth_domain(self):
        workspace = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
            study=workspace.study,
        )
        # Do not add the CDSA group to the auth domain.
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=self.cdsa_group,
        # )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedNoAccess)
        self.assertIsNone(record.data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_PRIMARY_AGREEMENT)

    def test_primary_inactive_in_auth_domain(self):
        workspace = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
            study=workspace.study,
        )
        # Add the CDSA group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, workspace_audit.RemoveAccess)
        self.assertIsNone(record.data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.INACTIVE_PRIMARY_AGREEMENT)

    def test_component_agreement_not_in_auth_domain(self):
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
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 1)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedNoAccess)
        self.assertIsNone(record.data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)

    def test_component_agreement_in_auth_domain(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        factories.DataAffiliateAgreementFactory.create(
            study=study, signed_agreement__is_primary=False
        )
        # Add the CDSA group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 1)
        record = cdsa_audit.errors[0]
        self.assertIsInstance(record, workspace_audit.RemoveAccess)
        self.assertIsNone(record.data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.NO_PRIMARY_AGREEMENT)

    def test_two_valid_primary_agreements_in_auth_domain(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        factories.DataAffiliateAgreementFactory.create(
            study=study, signed_agreement__version__major_version__version=1
        )
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study, signed_agreement__version__major_version__version=2
        )
        # Add the CDSA group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_two_valid_primary_agreements_same_major_version_in_auth_domain(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        major_version = factories.AgreementMajorVersionFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__version__major_version=major_version,
            signed_agreement__version__minor_version=1,
        )
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__version__major_version=major_version,
            signed_agreement__version__minor_version=2,
        )
        # Add the CDSA group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_two_valid_primary_agreements_not_in_auth_domain(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        factories.DataAffiliateAgreementFactory.create(
            study=study, signed_agreement__version__major_version__version=1
        )
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study, signed_agreement__version__major_version__version=2
        )
        # Do not add the CDSA group to the auth domain.
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=self.cdsa_group,
        # )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, workspace_audit.GrantAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_two_primary_one_valid_one_invalid_both_active_in_auth_domain(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__version__major_version__is_valid=True,
            signed_agreement__version__major_version__version=1,
        )
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__version__major_version__is_valid=False,
            signed_agreement__version__major_version__version=2,
        )
        # Add the CDSA group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_two_primary_one_valid_one_invalid_both_active_not_in_auth_domain(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__version__major_version__is_valid=True,
            signed_agreement__version__major_version__version=1,
        )
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__version__major_version__is_valid=False,
            signed_agreement__version__major_version__version=2,
        )
        # Do not add the CDSA group to the auth domain.
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=self.cdsa_group,
        # )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, workspace_audit.GrantAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_two_primary_one_active_one_inactive_in_auth_domain(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
        )
        # Add the CDSA group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_two_primary_one_active_one_inactive_not_in_auth_domain(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
        )
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
        )
        # Do not add the CDSA group to the auth domain.
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=self.cdsa_group,
        # )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, workspace_audit.GrantAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_two_primary_one_active_invalid_one_inactive_valid_in_auth_domain(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
            signed_agreement__version__major_version__is_valid=True,
        )
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
            signed_agreement__version__major_version__is_valid=False,
        )
        # Add the CDSA group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=self.cdsa_group,
        )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 1)
        self.assertEqual(len(cdsa_audit.needs_action), 0)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.verified[0]
        self.assertIsInstance(record, workspace_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_two_primary_one_active_invalid_one_inactive_valid_not_in_auth_domain(self):
        study = StudyFactory.create()
        workspace = factories.CDSAWorkspaceFactory.create(study=study)
        factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.WITHDRAWN,
            signed_agreement__version__major_version__is_valid=True,
        )
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(
            study=study,
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
            signed_agreement__version__major_version__is_valid=False,
        )
        # # Add the CDSA group to the auth domain.
        # GroupGroupMembershipFactory.create(
        #     parent_group=workspace.workspace.authorization_domains.first(),
        #     child_group=self.cdsa_group,
        # )
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        cdsa_audit._audit_workspace(workspace)
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, workspace_audit.GrantAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_no_workspaces(self):
        """Audit works when there are no workspaces."""
        cdsa_audit = workspace_audit.WorkspaceAccessAudit()
        self.assertFalse(cdsa_audit.completed)
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 0)
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
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)
        record = cdsa_audit.verified[1]
        self.assertIsInstance(record, workspace_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.workspace, workspace_2)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)
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
