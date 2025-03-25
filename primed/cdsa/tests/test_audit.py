# from datetime import timedelta

from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    GroupAccountMembershipFactory,
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
)
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory
from primed.users.tests.factories import UserFactory

from .. import models
from ..audit import accessor_audit, signed_agreement_audit, uploader_audit, workspace_audit
from . import factories

# from django.utils import timezone


class SignedAgreementAuditResultTest(TestCase):
    """General tests of the AuditResult dataclasses for SignedAgreements."""

    def setUp(self):
        super().setUp()
        self.cdsa_group = ManagedGroupFactory.create(name=settings.ANVIL_CDSA_GROUP_NAME)

    def test_verified_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.VerifiedAccess(
            signed_agreement=signed_agreement,
            note="foo",
        )
        self.assertIsNone(instance.action)
        self.assertEqual(
            instance.get_action_url(),
            reverse("cdsa:audit:signed_agreements:sag:resolve", args=[signed_agreement.cc_id]),
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
            reverse("cdsa:audit:signed_agreements:sag:resolve", args=[signed_agreement.cc_id]),
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
            reverse("cdsa:audit:signed_agreements:sag:resolve", args=[signed_agreement.cc_id]),
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
            reverse("cdsa:audit:signed_agreements:sag:resolve", args=[signed_agreement.cc_id]),
        )

    def test_error(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        instance = signed_agreement_audit.OtherError(
            signed_agreement=signed_agreement,
            note="foo",
        )
        self.assertEqual(
            instance.get_action_url(),
            reverse("cdsa:audit:signed_agreements:sag:resolve", args=[signed_agreement.cc_id]),
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
        self.cdsa_group = ManagedGroupFactory.create(name=settings.ANVIL_CDSA_GROUP_NAME)

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
            signed_agreement_queryset=models.SignedAgreement.objects.filter(pk=this_agreement.signed_agreement.pk)
        )
        cdsa_audit.run_audit()
        self.assertEqual(len(cdsa_audit.verified), 0)
        self.assertEqual(len(cdsa_audit.needs_action), 1)
        self.assertEqual(len(cdsa_audit.errors), 0)
        record = cdsa_audit.needs_action[0]
        self.assertIsInstance(record, signed_agreement_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, this_agreement.signed_agreement)
        self.assertEqual(record.note, cdsa_audit.ACTIVE_PRIMARY_AGREEMENT)

    def test_signed_agreement_queryset_wrong_class(self):
        """dbGaPAccessAudit raises error if signed_agreement_queryset has the wrong model class."""
        with self.assertRaises(ValueError) as e:
            signed_agreement_audit.SignedAgreementAccessAudit(
                signed_agreement_queryset=models.MemberAgreement.objects.all()
            )
        self.assertEqual(
            str(e.exception),
            "signed_agreement_queryset must be a queryset of SignedAgreement objects.",
        )

    def test_signed_agreement_queryset_not_queryset(self):
        """dbGaPAccessAudit raises error if signed_agreement_queryset is not a queryset."""
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
        this_agreement = factories.MemberAgreementFactory.create(is_primary=False, study_site=study_site)
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
        this_agreement = factories.MemberAgreementFactory.create(is_primary=False, study_site=study_site)
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
            is_primary=False,
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
            is_primary=False,
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
        this_agreement = factories.MemberAgreementFactory.create(is_primary=False, study_site=study_site)
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
        this_agreement = factories.MemberAgreementFactory.create(is_primary=False, study_site=study_site)
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
        this_agreement = factories.MemberAgreementFactory.create(is_primary=False, study_site=study_site)
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
        this_agreement = factories.MemberAgreementFactory.create(is_primary=False, study_site=study_site)
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
        this_agreement = factories.MemberAgreementFactory.create(is_primary=False, study_site=study_site)
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
        this_agreement = factories.MemberAgreementFactory.create(is_primary=False, study_site=study_site)
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
            is_primary=False,
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
            is_primary=False,
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
            is_primary=False,
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
            is_primary=False,
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
            is_primary=False,
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
            is_primary=False,
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
        this_agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False, study=study)
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
        this_agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False, study=study)
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
            is_primary=False,
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
            is_primary=False,
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
        this_agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False, study=study)
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
        this_agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False, study=study)
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
        this_agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False, study=study)
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
        this_agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False, study=study)
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
        this_agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False, study=study)
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
        this_agreement = factories.DataAffiliateAgreementFactory.create(is_primary=False, study=study)
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
            is_primary=False,
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
            is_primary=False,
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
            is_primary=False,
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
            is_primary=False,
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
            is_primary=False,
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
            is_primary=False,
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


class SignedAgreementAccessAuditTableTest(TestCase):
    """Tests for the `SignedAgreementAccessAuditTable` table."""

    def test_no_rows(self):
        """Table works with no rows."""
        table = signed_agreement_audit.SignedAgreementAccessAuditTable([])
        self.assertIsInstance(table, signed_agreement_audit.SignedAgreementAccessAuditTable)
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
        self.assertIsInstance(table, signed_agreement_audit.SignedAgreementAccessAuditTable)
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
        self.assertIsInstance(table, signed_agreement_audit.SignedAgreementAccessAuditTable)
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
        self.cdsa_group = ManagedGroupFactory.create(name=settings.ANVIL_CDSA_GROUP_NAME)
        self.study = StudyFactory.create()

    def test_verified_access(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(study=self.study)
        instance = workspace_audit.VerifiedAccess(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        self.assertEqual(
            instance.get_action_url(),
            reverse(
                "cdsa:audit:workspaces:resolve",
                args=[
                    workspace.workspace.billing_project.name,
                    workspace.workspace.name,
                ],
            ),
        )

    def test_verified_no_access(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(study=self.study)
        instance = workspace_audit.VerifiedNoAccess(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        self.assertEqual(
            instance.get_action_url(),
            reverse(
                "cdsa:audit:workspaces:resolve",
                args=[
                    workspace.workspace.billing_project.name,
                    workspace.workspace.name,
                ],
            ),
        )

    def test_grant_access(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(study=self.study)
        instance = workspace_audit.GrantAccess(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        self.assertEqual(
            instance.get_action_url(),
            reverse(
                "cdsa:audit:workspaces:resolve",
                args=[
                    workspace.workspace.billing_project.name,
                    workspace.workspace.name,
                ],
            ),
        )

    def test_remove_access(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(study=self.study)
        instance = workspace_audit.RemoveAccess(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        self.assertEqual(
            instance.get_action_url(),
            reverse(
                "cdsa:audit:workspaces:resolve",
                args=[
                    workspace.workspace.billing_project.name,
                    workspace.workspace.name,
                ],
            ),
        )

    def test_error(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(study=self.study)
        instance = workspace_audit.OtherError(
            workspace=workspace,
            data_affiliate_agreement=data_affiliate_agreement,
            note="foo",
        )
        self.assertEqual(
            instance.get_action_url(),
            reverse(
                "cdsa:audit:workspaces:resolve",
                args=[
                    workspace.workspace.billing_project.name,
                    workspace.workspace.name,
                ],
            ),
        )

    def test_error_no_data_affiliate_agreement(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        instance = workspace_audit.OtherError(
            workspace=workspace,
            note="foo",
        )
        self.assertEqual(
            instance.get_action_url(),
            reverse(
                "cdsa:audit:workspaces:resolve",
                args=[
                    workspace.workspace.billing_project.name,
                    workspace.workspace.name,
                ],
            ),
        )

    def test_anvil_group_name(self):
        workspace = factories.CDSAWorkspaceFactory.create(study=self.study)
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(study=self.study)
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
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(study=self.study)
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
        self.cdsa_group = ManagedGroupFactory.create(name=settings.ANVIL_CDSA_GROUP_NAME)

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
            cdsa_workspace_queryset=models.CDSAWorkspace.objects.filter(pk=cdsa_workspace.workspace.pk)
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
        """Audit raises error if signed_agreement_queryset has the wrong model class."""
        with self.assertRaises(ValueError) as e:
            workspace_audit.WorkspaceAccessAudit(cdsa_workspace_queryset=models.SignedAgreement.objects.all())
        self.assertEqual(
            str(e.exception),
            "cdsa_workspace_queryset must be a queryset of CDSAWorkspace objects.",
        )

    def test_cdsa_workspace_queryset_not_queryset(self):
        """Audit raises error if signed_agreement_queryset is not a queryset."""
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
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(study=study)
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
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(study=study)
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
        factories.DataAffiliateAgreementFactory.create(study=study, is_primary=False)
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
        factories.DataAffiliateAgreementFactory.create(study=study, is_primary=False)
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
        factories.DataAffiliateAgreementFactory.create(study=study, signed_agreement__version__major_version__version=1)
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
        factories.DataAffiliateAgreementFactory.create(study=study, signed_agreement__version__major_version__version=1)
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
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create(study=study)
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


class AccessorAuditResultTest(TestCase):
    """General tests of the AccessorAuditResult dataclasses for SignedAgreements."""

    def setUp(self):
        super().setUp()
        self.cdsa_group = ManagedGroupFactory.create(name=settings.ANVIL_CDSA_GROUP_NAME)

    def test_verified_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        account = AccountFactory.create()
        instance = accessor_audit.VerifiedAccess(
            signed_agreement=signed_agreement,
            member=account,
            note="foo",
        )
        self.assertIsNone(instance.action)

    def test_verified_no_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        account = AccountFactory.create()
        instance = accessor_audit.VerifiedNoAccess(
            signed_agreement=signed_agreement,
            member=account,
            note="foo",
        )
        self.assertIsNone(instance.action)

    def test_grant_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        account = AccountFactory.create()
        instance = accessor_audit.GrantAccess(
            signed_agreement=signed_agreement,
            member=account,
            note="foo",
        )
        self.assertEqual(instance.action, "Grant access")

    def test_remove_access(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        account = AccountFactory.create()
        instance = accessor_audit.RemoveAccess(
            signed_agreement=signed_agreement,
            member=account,
            note="foo",
        )
        self.assertEqual(instance.action, "Remove access")

    def test_error(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        account = AccountFactory.create()
        instance = accessor_audit.Error(
            signed_agreement=signed_agreement,
            member=account,
            note="foo",
            has_access=False,
        )
        self.assertIsNone(instance.action)

    def test_post_init_account_and_user_do_not_match(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        account = AccountFactory.create()
        user = UserFactory.create()
        with self.assertRaises(ValueError) as e:
            accessor_audit.VerifiedAccess(
                signed_agreement=signed_agreement,
                member=account,
                user=user,
                note="foo",
            )
        self.assertEqual(str(e.exception), "Account and user do not match.")

    def test_post_init_user_and_group(self):
        signed_agreement = factories.SignedAgreementFactory.create()
        group = ManagedGroupFactory.create()
        user = UserFactory.create()
        with self.assertRaises(ValueError) as e:
            accessor_audit.VerifiedAccess(
                signed_agreement=signed_agreement,
                member=group,
                user=user,
                note="foo",
            )
        self.assertEqual(str(e.exception), "Cannot specify both a ManagedGroup member and a User.")


class AccessorAuditTableTest(TestCase):
    """Tests for the `AccessorAuditTable` table."""

    def test_no_rows(self):
        """Table works with no rows."""
        table = accessor_audit.AccessorAuditTable([])
        self.assertIsInstance(table, accessor_audit.AccessorAuditTable)
        self.assertEqual(len(table.rows), 0)

    def test_one_row(self):
        """Table works with one row."""
        member_agreement = factories.MemberAgreementFactory.create()
        account = AccountFactory.create(verified=True)
        data = [
            {
                "signed_agreement": member_agreement.signed_agreement,
                "user": account.user,
                "member": account,
                "has_access": True,
                "note": "a note",
            }
        ]
        table = accessor_audit.AccessorAuditTable(data)
        self.assertIsInstance(table, accessor_audit.AccessorAuditTable)
        self.assertEqual(len(table.rows), 1)
        self.assertIn(
            str(member_agreement.signed_agreement.cc_id),
            table.rows[0].get_cell("signed_agreement"),
        )
        self.assertEqual(table.rows[0].get_cell("note"), "a note")

    def test_two_rows(self):
        """Table works with two rows."""
        member_agreement_1 = factories.MemberAgreementFactory.create()
        member_agreement_2 = factories.DataAffiliateAgreementFactory.create()
        account_1 = AccountFactory.create(verified=True)
        account_2 = AccountFactory.create(verified=True)
        data = [
            {
                "signed_agreement": member_agreement_1.signed_agreement,
                "user": account_1.user,
                "member": account_1,
                "has_access": True,
                "note": "note 1",
            },
            {
                "signed_agreement": member_agreement_2.signed_agreement,
                "user": account_2.user,
                "member": account_2,
                "has_access": True,
                "note": "note 2",
            },
        ]
        table = accessor_audit.AccessorAuditTable(data)
        self.assertIsInstance(table, accessor_audit.AccessorAuditTable)
        self.assertEqual(len(table.rows), 2)
        self.assertIn(
            str(member_agreement_1.signed_agreement.cc_id),
            table.rows[0].get_cell("signed_agreement"),
        )
        self.assertEqual(table.rows[0].get_cell("note"), "note 1")
        self.assertIn(
            str(member_agreement_2.signed_agreement.cc_id),
            table.rows[1].get_cell("signed_agreement"),
        )
        self.assertEqual(table.rows[1].get_cell("note"), "note 2")


class UploaderAuditResultTest(TestCase):
    """General tests of the UploaderAuditResult dataclasses for DataAffiliateAgreements."""

    def setUp(self):
        super().setUp()
        self.cdsa_group = ManagedGroupFactory.create(name=settings.ANVIL_CDSA_GROUP_NAME)

    def test_verified_access(self):
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create()
        instance = uploader_audit.VerifiedAccess(
            data_affiliate_agreement=data_affiliate_agreement,
            member=account,
            note="foo",
        )
        self.assertIsNone(instance.action)

    def test_verified_no_access(self):
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create()
        instance = uploader_audit.VerifiedNoAccess(
            data_affiliate_agreement=data_affiliate_agreement,
            member=account,
            note="foo",
        )
        self.assertIsNone(instance.action)

    def test_grant_access(self):
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create()
        instance = uploader_audit.GrantAccess(
            data_affiliate_agreement=data_affiliate_agreement,
            member=account,
            note="foo",
        )
        self.assertEqual(instance.action, "Grant access")

    def test_remove_access(self):
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create()
        instance = uploader_audit.RemoveAccess(
            data_affiliate_agreement=data_affiliate_agreement,
            member=account,
            note="foo",
        )
        self.assertEqual(instance.action, "Remove access")

    def test_error(self):
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create()
        instance = uploader_audit.Error(
            data_affiliate_agreement=data_affiliate_agreement,
            member=account,
            note="foo",
            has_access=False,
        )
        self.assertIsNone(instance.action)

    def test_post_init_account_and_user_do_not_match(self):
        agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create()
        user = UserFactory.create()
        with self.assertRaises(ValueError) as e:
            uploader_audit.VerifiedAccess(
                data_affiliate_agreement=agreement,
                member=account,
                user=user,
                note="foo",
            )
        self.assertEqual(str(e.exception), "Account and user do not match.")

    def test_post_init_user_and_group(self):
        agreement = factories.DataAffiliateAgreementFactory.create()
        group = ManagedGroupFactory.create()
        user = UserFactory.create()
        with self.assertRaises(ValueError) as e:
            uploader_audit.VerifiedAccess(
                data_affiliate_agreement=agreement,
                member=group,
                user=user,
                note="foo",
            )
        self.assertEqual(str(e.exception), "Cannot specify both a ManagedGroup member and a User.")


class UploaderAuditTableTest(TestCase):
    """Tests for the `UploaderAuditTable` table."""

    def test_no_rows(self):
        """Table works with no rows."""
        table = uploader_audit.UploaderAuditTable([])
        self.assertIsInstance(table, uploader_audit.UploaderAuditTable)
        self.assertEqual(len(table.rows), 0)

    def test_one_row(self):
        """Table works with one row."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create(verified=True)
        data = [
            {
                "data_affiliate_agreement": data_affiliate_agreement,
                "user": account.user,
                "member": account,
                "has_access": True,
                "note": "a note",
            }
        ]
        table = uploader_audit.UploaderAuditTable(data)
        self.assertIsInstance(table, uploader_audit.UploaderAuditTable)
        self.assertEqual(len(table.rows), 1)
        self.assertIn(
            str(data_affiliate_agreement.signed_agreement.cc_id),
            table.rows[0].get_cell("data_affiliate_agreement"),
        )
        self.assertEqual(table.rows[0].get_cell("note"), "a note")

    def test_two_rows(self):
        """Table works with two rows."""
        data_affiliate_agreement_1 = factories.DataAffiliateAgreementFactory.create()
        data_affiliate_agreement_2 = factories.DataAffiliateAgreementFactory.create()
        account_1 = AccountFactory.create(verified=True)
        account_2 = AccountFactory.create(verified=True)
        data = [
            {
                "data_affiliate_agreement": data_affiliate_agreement_1,
                "user": account_1.user,
                "member": account_1,
                "has_access": True,
                "note": "note 1",
            },
            {
                "data_affiliate_agreement": data_affiliate_agreement_2,
                "user": account_2.user,
                "member": account_2,
                "has_access": True,
                "note": "note 2",
            },
        ]
        table = uploader_audit.UploaderAuditTable(data)
        self.assertIsInstance(table, uploader_audit.UploaderAuditTable)
        self.assertEqual(len(table.rows), 2)
        self.assertIn(
            str(data_affiliate_agreement_1.signed_agreement.cc_id),
            table.rows[0].get_cell("data_affiliate_agreement"),
        )
        self.assertEqual(table.rows[0].get_cell("note"), "note 1")
        self.assertIn(
            str(data_affiliate_agreement_2.signed_agreement.cc_id),
            table.rows[1].get_cell("data_affiliate_agreement"),
        )
        self.assertEqual(table.rows[1].get_cell("note"), "note 2")


class AccessorAuditTest(TestCase):
    """Tests for the AccessorAudit classes."""

    def test_completed(self):
        """completed is updated properly."""
        audit = accessor_audit.AccessorAudit()
        self.assertFalse(audit.completed)
        audit.run_audit()
        self.assertTrue(audit.completed)

    def test_no_applications(self):
        """Audit works if there are no SignedAgreements."""
        audit = accessor_audit.AccessorAudit()
        audit.run_audit()
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)

    def test_audit_agreement_and_object_user(self):
        """audit_agreement_and_object works when passed a user object."""
        signed_agreement = factories.SignedAgreementFactory.create()
        user = UserFactory.create()
        audit = accessor_audit.AccessorAudit()
        audit.audit_agreement_and_object(signed_agreement, user)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.NOT_ACCESSOR)

    def test_audit_agreement_and_object_account(self):
        """audit_agreement_and_object works when passed an Account object."""
        signed_agreement = factories.SignedAgreementFactory.create()
        account = AccountFactory.create()
        audit = accessor_audit.AccessorAudit()
        audit.audit_agreement_and_object(signed_agreement, account)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_audit_agreement_and_object_group(self):
        """audit_agreement_and_object works when passed a ManagedGroup object."""
        signed_agreement = factories.SignedAgreementFactory.create()
        group = ManagedGroupFactory.create()
        audit = accessor_audit.AccessorAudit()
        audit.audit_agreement_and_object(signed_agreement, group)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.GROUP_WITHOUT_ACCESS)

    def test_audit_agreement_and_object_user_email(self):
        """audit_agreement_and_object works when passed a string email for a user."""
        signed_agreement = factories.SignedAgreementFactory.create()
        user = UserFactory.create()
        audit = accessor_audit.AccessorAudit()
        audit.audit_agreement_and_object(signed_agreement, user.username)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.NOT_ACCESSOR)

    def test_audit_agreement_and_object_user_email_case_insensitive(self):
        """audit_agreement_and_object works when passed a string email for a user."""
        signed_agreement = factories.SignedAgreementFactory.create()
        user = UserFactory.create(username="foo@BAR.com")
        audit = accessor_audit.AccessorAudit()
        audit.audit_agreement_and_object(signed_agreement, "FOO@bar.com")
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.NOT_ACCESSOR)

    def test_audit_agreement_and_object_account_email(self):
        """audit_agreement_and_object works when passed a string email for an account."""
        signed_agreement = factories.SignedAgreementFactory.create()
        account = AccountFactory.create()
        audit = accessor_audit.AccessorAudit()
        audit.audit_agreement_and_object(signed_agreement, account.email)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_audit_agreement_and_object_account_email_case_insensitive(self):
        """audit_agreement_and_object works when passed a string email for an account."""
        signed_agreement = factories.SignedAgreementFactory.create()
        account = AccountFactory.create(email="foo@BAR.com")
        audit = accessor_audit.AccessorAudit()
        audit.audit_agreement_and_object(signed_agreement, "FOO@bar.com")
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_audit_agreement_and_object_group_email(self):
        """audit_agreement_and_object works when passed a string email for a ManagedGroup."""
        signed_agreement = factories.SignedAgreementFactory.create()
        group = ManagedGroupFactory.create()
        audit = accessor_audit.AccessorAudit()
        audit.audit_agreement_and_object(signed_agreement, group.email)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.GROUP_WITHOUT_ACCESS)

    def test_audit_agreement_and_object_group_email_case_insensitive(self):
        """audit_agreement_and_object works when passed a string email for a ManagedGroup."""
        signed_agreement = factories.SignedAgreementFactory.create()
        group = ManagedGroupFactory.create(email="foo@BAR.com")
        audit = accessor_audit.AccessorAudit()
        audit.audit_agreement_and_object(signed_agreement, "FOO@bar.com")
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.GROUP_WITHOUT_ACCESS)

    def test_audit_agreement_and_object_email_does_not_exist(self):
        """audit_agreement_and_object works when passed a ManagedGroup object."""
        signed_agreement = factories.SignedAgreementFactory.create()
        audit = accessor_audit.AccessorAudit()
        with self.assertRaises(ValueError) as e:
            audit.audit_agreement_and_object(signed_agreement, "foo@bar.com")
        self.assertIn(
            "Could not find",
            str(e.exception),
        )

    def test_audit_agreement_and_object_other_object(self):
        """audit_agreement_and_object raises ValueError when passed an incorrect object."""
        signed_agreement = factories.SignedAgreementFactory.create()
        audit = accessor_audit.AccessorAudit()
        with self.assertRaises(ValueError):
            audit.audit_agreement_and_object(signed_agreement, object)

    def test_accessor_linked_account_in_access_group(self):
        # Create agreement.
        signed_agreement = factories.SignedAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up accessors.
        signed_agreement.accessors.add(account.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=signed_agreement.anvil_access_group, account=account)
        # Set up audit
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCESSOR_IN_ACCESS_GROUP)

    def test_accessor_linked_account_not_in_access_group(self):
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up accessors.
        signed_agreement.accessors.add(account.user)
        # Access group membership.
        # GroupAccountMembershipFactory.create(group=signed_agreement.anvil_access_group, account=account)
        # Set up audit
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.needs_action[0]
        self.assertIsInstance(record, accessor_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCESSOR_LINKED_ACCOUNT)

    def test_accessor_no_account(self):
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        # Create accounts.
        user = UserFactory.create()
        # account = AccountFactory.create(verified=True)
        # Set up accessors.
        signed_agreement.accessors.add(user)
        # Access group membership.
        # GroupAccountMembershipFactory.create(group=signed_agreement.anvil_access_group, account=account)
        # Set up audit
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCESSOR_NO_ACCOUNT)

    def test_user_in_group_not_accessor(self):
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up accessors.
        # signed_agreement.accessors.add(account.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=signed_agreement.anvil_access_group, account=account)
        # Set up audit
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.needs_action[0]
        self.assertIsInstance(record, accessor_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.NOT_ACCESSOR)

    def test_not_accessor_and_account_has_no_user(self):
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create()
        # Set up accessors.
        # signed_agreement.accessors.add(account.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=signed_agreement.anvil_access_group, account=account)
        # Set up audit
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.needs_action[0]
        self.assertIsInstance(record, accessor_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_accessor_inactive_account_not_in_access_group(self):
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up accessors.
        signed_agreement.accessors.add(account.user)
        # Deactivate account.
        account.deactivate()
        # Set up audit
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.INACTIVE_ACCOUNT)

    def test_accessor_inactive_account_in_access_group(self):
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up accessors.
        signed_agreement.accessors.add(account.user)
        # Deactivate account.
        account.deactivate()
        # Access group membership.
        GroupAccountMembershipFactory.create(group=signed_agreement.anvil_access_group, account=account)
        # Set up audit
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.needs_action[0]
        self.assertIsInstance(record, accessor_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.INACTIVE_ACCOUNT)

    def test_two_accessors(self):
        """Audit works when there are two accessors."""
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        # Create accounts.
        account_1 = AccountFactory.create(verified=True)
        account_2 = AccountFactory.create(verified=True)
        # Set up accessors.
        signed_agreement.accessors.add(account_1.user, account_2.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=signed_agreement.anvil_access_group, account=account_1)
        # Set up audit
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 1)  # One of the accessors.
        self.assertEqual(len(audit.needs_action), 1)  # The other accessor.
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, account_1.user)
        self.assertEqual(record.member, account_1)
        self.assertEqual(record.note, audit.ACCESSOR_IN_ACCESS_GROUP)
        record = audit.needs_action[0]
        self.assertIsInstance(record, accessor_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, account_2.user)
        self.assertEqual(record.member, account_2)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCESSOR_LINKED_ACCOUNT)

    def test_unexpected_group_in_access_group(self):
        """A group unexpectedly has access."""
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        # Add a group to the access group.
        group = ManagedGroupFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=signed_agreement.anvil_access_group,
            child_group=group,
        )
        # Set up audit
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 1)
        record = audit.errors[0]
        self.assertIsInstance(record, accessor_audit.RemoveAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.UNEXPECTED_GROUP_ACCESS)

    def test_representative_not_accessor(self):
        """Representative is not an accessor."""
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)

    def test_representative_is_accessor(self):
        """Representative is also an accessor."""
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        signed_agreement.accessors.add(signed_agreement.representative)
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement)
        self.assertEqual(record.user, signed_agreement.representative)
        self.assertIsNone(record.member)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCESSOR_NO_ACCOUNT)

    def test_ignores_admins_group(self):
        """Ignores the admin group."""
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        # Add a group to the access group.
        group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")
        GroupGroupMembershipFactory.create(
            parent_group=signed_agreement.anvil_access_group,
            child_group=group,
        )
        # Set up audit
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        # Check the sub-method specifically.
        audit = accessor_audit.AccessorAudit()
        audit.audit_agreement_and_object(signed_agreement, group)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="TEST_FOO")
    def test_ignores_admins_group_different_setting(self):
        """Ignores the admin group found in settings file."""
        # Create applications.
        signed_agreement = factories.SignedAgreementFactory.create()
        # Add a group to the access group.
        group = ManagedGroupFactory.create(name="TEST_FOO")
        GroupGroupMembershipFactory.create(
            parent_group=signed_agreement.anvil_access_group,
            child_group=group,
        )
        # Set up audit
        audit = accessor_audit.AccessorAudit()
        # Run audit
        audit.audit_agreement(signed_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        # Check the sub-method specifically.
        audit = accessor_audit.AccessorAudit()
        audit.audit_agreement_and_object(signed_agreement, group)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)

    def test_two_agreements(self):
        """Audit works with two SignedAgreements."""
        signed_agreement_1 = factories.SignedAgreementFactory.create()
        account_1 = AccountFactory.create(verified=True)
        signed_agreement_1.accessors.add(account_1.user)
        signed_agreement_2 = factories.SignedAgreementFactory.create()
        user_2 = UserFactory.create()
        signed_agreement_2.accessors.add(user_2)
        audit = accessor_audit.AccessorAudit()
        audit.run_audit()
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, accessor_audit.VerifiedNoAccess)
        self.assertEqual(record.signed_agreement, signed_agreement_2)
        self.assertEqual(record.user, user_2)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCESSOR_NO_ACCOUNT)
        record = audit.needs_action[0]
        self.assertIsInstance(record, accessor_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, signed_agreement_1)
        self.assertEqual(record.user, account_1.user)
        self.assertEqual(record.member, account_1)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCESSOR_LINKED_ACCOUNT)

    def test_queryset(self):
        """Audit only runs on the specified queryset of SignedAgreements."""
        signed_agreement_1 = factories.SignedAgreementFactory.create()
        account_1 = AccountFactory.create(verified=True)
        signed_agreement_1.accessors.add(account_1.user)
        signed_agreement_2 = factories.SignedAgreementFactory.create()
        # First application
        audit = accessor_audit.AccessorAudit(queryset=models.SignedAgreement.objects.filter(pk=signed_agreement_1.pk))
        audit.run_audit()
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.needs_action[0]
        self.assertIsInstance(record, accessor_audit.GrantAccess)
        self.assertEqual(record.signed_agreement, signed_agreement_1)
        self.assertEqual(record.user, account_1.user)
        self.assertEqual(record.member, account_1)
        self.assertEqual(record.note, accessor_audit.AccessorAudit.ACCESSOR_LINKED_ACCOUNT)
        # Second application
        audit = accessor_audit.AccessorAudit(queryset=models.SignedAgreement.objects.filter(pk=signed_agreement_2.pk))
        audit.run_audit()
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)

    def test_queryset_wrong_class(self):
        """Raises ValueError if queryset is not a QuerySet."""
        with self.assertRaises(ValueError):
            accessor_audit.AccessorAudit(queryset="foo")
        with self.assertRaises(ValueError):
            accessor_audit.AccessorAudit(queryset=models.MemberAgreement.objects.all())


class DataAffiliateAgreementUploaderAuditTest(TestCase):
    """Tests for the DataAffiliateAgreementUploaderAudit classes."""

    def test_completed(self):
        """completed is updated properly."""
        audit = uploader_audit.UploaderAudit()
        self.assertFalse(audit.completed)
        audit.run_audit()
        self.assertTrue(audit.completed)

    def test_no_applications(self):
        """Audit works if there are no DataAffiliateAgreements."""
        audit = uploader_audit.UploaderAudit()
        audit.run_audit()
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)

    def test_audit_agreement_and_object_user(self):
        """audit_agreement_and_object works when passed a user object."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        user = UserFactory.create()
        audit = uploader_audit.UploaderAudit()
        audit.audit_agreement_and_object(data_affiliate_agreement, user)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.NOT_UPLOADER)

    def test_audit_agreement_and_object_account(self):
        """audit_agreement_and_object works when passed an Account object."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create()
        audit = uploader_audit.UploaderAudit()
        audit.audit_agreement_and_object(data_affiliate_agreement, account)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_audit_agreement_and_object_group(self):
        """audit_agreement_and_object works when passed a ManagedGroup object."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        group = ManagedGroupFactory.create()
        audit = uploader_audit.UploaderAudit()
        audit.audit_agreement_and_object(data_affiliate_agreement, group)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.GROUP_WITHOUT_ACCESS)

    def test_audit_agreement_and_object_user_email(self):
        """audit_agreement_and_object works when passed a string email for a user."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        user = UserFactory.create()
        audit = uploader_audit.UploaderAudit()
        audit.audit_agreement_and_object(data_affiliate_agreement, user.username)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.NOT_UPLOADER)

    def test_audit_agreement_and_object_user_email_case_insensitive(self):
        """audit_agreement_and_object works when passed a string email for a user."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        user = UserFactory.create(username="foo@BAR.com")
        audit = uploader_audit.UploaderAudit()
        audit.audit_agreement_and_object(data_affiliate_agreement, "FOO@bar.com")
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.NOT_UPLOADER)

    def test_audit_agreement_and_object_account_email(self):
        """audit_agreement_and_object works when passed a string email for an account."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create()
        audit = uploader_audit.UploaderAudit()
        audit.audit_agreement_and_object(data_affiliate_agreement, account.email)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_audit_agreement_and_object_account_email_case_insensitive(self):
        """audit_agreement_and_object works when passed a string email for an account."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        account = AccountFactory.create(email="foo@BAR.com")
        audit = uploader_audit.UploaderAudit()
        audit.audit_agreement_and_object(data_affiliate_agreement, "FOO@bar.com")
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_audit_agreement_and_object_group_email(self):
        """audit_agreement_and_object works when passed a string email for a ManagedGroup."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        group = ManagedGroupFactory.create()
        audit = uploader_audit.UploaderAudit()
        audit.audit_agreement_and_object(data_affiliate_agreement, group.email)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.GROUP_WITHOUT_ACCESS)

    def test_audit_agreement_and_object_group_email_case_insensitive(self):
        """audit_agreement_and_object works when passed a string email for a ManagedGroup."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        group = ManagedGroupFactory.create(email="foo@BAR.com")
        audit = uploader_audit.UploaderAudit()
        audit.audit_agreement_and_object(data_affiliate_agreement, "FOO@bar.com")
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.GROUP_WITHOUT_ACCESS)

    def test_audit_agreement_and_object_email_does_not_exist(self):
        """audit_agreement_and_object works when passed a ManagedGroup object."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        audit = uploader_audit.UploaderAudit()
        with self.assertRaises(ValueError) as e:
            audit.audit_agreement_and_object(data_affiliate_agreement, "foo@bar.com")
        self.assertIn(
            "Could not find",
            str(e.exception),
        )

    def test_audit_agreement_and_object_other_object(self):
        """audit_agreement_and_object raises ValueError when passed an incorrect object."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        audit = uploader_audit.UploaderAudit()
        with self.assertRaises(ValueError):
            audit.audit_agreement_and_object(data_affiliate_agreement, object)

    def test_uploader_linked_account_in_access_group(self):
        # Create agreement.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up uploaders.
        data_affiliate_agreement.uploaders.add(account.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=data_affiliate_agreement.anvil_upload_group, account=account)
        # Set up audit
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.UPLOADER_IN_ACCESS_GROUP)

    def test_uploader_linked_account_not_in_access_group(self):
        # Create applications.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up uploaders.
        data_affiliate_agreement.uploaders.add(account.user)
        # Access group membership.
        # GroupAccountMembershipFactory.create(group=data_affiliate_agreement.anvil_upload_group, account=account)
        # Set up audit
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.needs_action[0]
        self.assertIsInstance(record, uploader_audit.GrantAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.UPLOADER_LINKED_ACCOUNT)

    def test_uploader_no_account(self):
        # Create applications.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        # Create accounts.
        user = UserFactory.create()
        # account = AccountFactory.create(verified=True)
        # Set up uploaders.
        data_affiliate_agreement.uploaders.add(user)
        # Access group membership.
        # GroupAccountMembershipFactory.create(group=data_affiliate_agreement.anvil_upload_group, account=account)
        # Set up audit
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, user)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.UPLOADER_NO_ACCOUNT)

    def test_uploader_inactive_account_not_in_access_group(self):
        # Create agreement.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up uploaders.
        data_affiliate_agreement.uploaders.add(account.user)
        # Deactivate account.
        account.deactivate()
        # Set up audit
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.INACTIVE_ACCOUNT)

    def test_uploader_inactive_account_in_access_group(self):
        # Create agreement.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up uploaders.
        data_affiliate_agreement.uploaders.add(account.user)
        # Deactivate account.
        account.deactivate()
        # Access group membership.
        GroupAccountMembershipFactory.create(group=data_affiliate_agreement.anvil_upload_group, account=account)
        # Set up audit
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.needs_action[0]
        self.assertIsInstance(record, uploader_audit.RemoveAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.INACTIVE_ACCOUNT)

    def test_user_in_group_not_uploader(self):
        # Create applications.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create(verified=True)
        # Set up uploaders.
        # data_affiliate_agreement.uploaders.add(account.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=data_affiliate_agreement.anvil_upload_group, account=account)
        # Set up audit
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.needs_action[0]
        self.assertIsInstance(record, uploader_audit.RemoveAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, account.user)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.NOT_UPLOADER)

    def test_not_uploader_and_account_has_no_user(self):
        # Create applications.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        # Create accounts.
        account = AccountFactory.create()
        # Set up uploaders.
        # data_affiliate_agreement.uploaders.add(account.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=data_affiliate_agreement.anvil_upload_group, account=account)
        # Set up audit
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.needs_action[0]
        self.assertIsInstance(record, uploader_audit.RemoveAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, account)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.ACCOUNT_NOT_LINKED_TO_USER)

    def test_two_uploaders(self):
        """Audit works when there are two uploaders."""
        # Create applications.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        # Create accounts.
        account_1 = AccountFactory.create(verified=True)
        account_2 = AccountFactory.create(verified=True)
        # Set up uploaders.
        data_affiliate_agreement.uploaders.add(account_1.user, account_2.user)
        # Access group membership.
        GroupAccountMembershipFactory.create(group=data_affiliate_agreement.anvil_upload_group, account=account_1)
        # Set up audit
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 1)  # One of the uploaders.
        self.assertEqual(len(audit.needs_action), 1)  # The other uploader.
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, account_1.user)
        self.assertEqual(record.member, account_1)
        self.assertEqual(record.note, audit.UPLOADER_IN_ACCESS_GROUP)
        record = audit.needs_action[0]
        self.assertIsInstance(record, uploader_audit.GrantAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, account_2.user)
        self.assertEqual(record.member, account_2)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.UPLOADER_LINKED_ACCOUNT)

    def test_unexpected_group_in_access_group(self):
        """A group unexpectedly has access."""
        # Create applications.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        # Add a group to the access group.
        group = ManagedGroupFactory.create()
        GroupGroupMembershipFactory.create(
            parent_group=data_affiliate_agreement.anvil_upload_group,
            child_group=group,
        )
        # Set up audit
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 1)
        record = audit.errors[0]
        self.assertIsInstance(record, uploader_audit.RemoveAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, None)
        self.assertEqual(record.member, group)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.UNEXPECTED_GROUP_ACCESS)

    def test_representative_not_uploader(self):
        """Representative is not an uploader."""
        # Create applications.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)

    def test_representative_is_uploader(self):
        """Representative is also an uploader."""
        # Create applications.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        data_affiliate_agreement.uploaders.add(data_affiliate_agreement.signed_agreement.representative)
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement)
        self.assertEqual(record.user, data_affiliate_agreement.signed_agreement.representative)
        self.assertIsNone(record.member)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.UPLOADER_NO_ACCOUNT)

    def test_ignores_admins_group(self):
        """Ignores the admin group."""
        # Create applications.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        # Add a group to the access group.
        group = ManagedGroupFactory.create(name="TEST_PRIMED_CC_ADMINS")
        GroupGroupMembershipFactory.create(
            parent_group=data_affiliate_agreement.anvil_upload_group,
            child_group=group,
        )
        # Set up audit
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        # Check the sub-method specifically.
        audit = uploader_audit.UploaderAudit()
        audit.audit_agreement_and_object(data_affiliate_agreement, group)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)

    @override_settings(ANVIL_CC_ADMINS_GROUP_NAME="TEST_FOO")
    def test_ignores_admins_group_different_setting(self):
        """Ignores the admin group found in settings file."""
        # Create applications.
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        # Add a group to the access group.
        group = ManagedGroupFactory.create(name="TEST_FOO")
        GroupGroupMembershipFactory.create(
            parent_group=data_affiliate_agreement.anvil_upload_group,
            child_group=group,
        )
        # Set up audit
        audit = uploader_audit.UploaderAudit()
        # Run audit
        audit.audit_agreement(data_affiliate_agreement)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)
        # Check the sub-method specifically.
        audit = uploader_audit.UploaderAudit()
        audit.audit_agreement_and_object(data_affiliate_agreement, group)
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)

    def test_two_agreements(self):
        """Audit works with two DataAffiliateAgreements."""
        data_affiliate_agreement_1 = factories.DataAffiliateAgreementFactory.create()
        account_1 = AccountFactory.create(verified=True)
        data_affiliate_agreement_1.uploaders.add(account_1.user)
        data_affiliate_agreement_2 = factories.DataAffiliateAgreementFactory.create()
        user_2 = UserFactory.create()
        data_affiliate_agreement_2.uploaders.add(user_2)
        audit = uploader_audit.UploaderAudit()
        audit.run_audit()
        self.assertEqual(len(audit.verified), 1)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.verified[0]
        self.assertIsInstance(record, uploader_audit.VerifiedNoAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement_2)
        self.assertEqual(record.user, user_2)
        self.assertEqual(record.member, None)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.UPLOADER_NO_ACCOUNT)
        record = audit.needs_action[0]
        self.assertIsInstance(record, uploader_audit.GrantAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement_1)
        self.assertEqual(record.user, account_1.user)
        self.assertEqual(record.member, account_1)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.UPLOADER_LINKED_ACCOUNT)

    def test_queryset(self):
        """Audit only runs on the specified queryset of DataAffiliateAgreements."""
        data_affiliate_agreement_1 = factories.DataAffiliateAgreementFactory.create()
        account_1 = AccountFactory.create(verified=True)
        data_affiliate_agreement_1.uploaders.add(account_1.user)
        data_affiliate_agreement_2 = factories.DataAffiliateAgreementFactory.create()
        # First application
        audit = uploader_audit.UploaderAudit(
            queryset=models.DataAffiliateAgreement.objects.filter(pk=data_affiliate_agreement_1.pk)
        )
        audit.run_audit()
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 1)
        self.assertEqual(len(audit.errors), 0)
        record = audit.needs_action[0]
        self.assertIsInstance(record, uploader_audit.GrantAccess)
        self.assertEqual(record.data_affiliate_agreement, data_affiliate_agreement_1)
        self.assertEqual(record.user, account_1.user)
        self.assertEqual(record.member, account_1)
        self.assertEqual(record.note, uploader_audit.UploaderAudit.UPLOADER_LINKED_ACCOUNT)
        # Second application
        audit = uploader_audit.UploaderAudit(
            queryset=models.DataAffiliateAgreement.objects.filter(pk=data_affiliate_agreement_2.pk)
        )
        audit.run_audit()
        self.assertEqual(len(audit.verified), 0)
        self.assertEqual(len(audit.needs_action), 0)
        self.assertEqual(len(audit.errors), 0)

    def test_queryset_wrong_class(self):
        """Raises ValueError if queryset is not a QuerySet."""
        with self.assertRaises(ValueError):
            uploader_audit.UploaderAudit(queryset="foo")
        with self.assertRaises(ValueError):
            uploader_audit.UploaderAudit(queryset=models.SignedAgreement.objects.all())

    def test_queryset_only_data_affiliates(self):
        """Only DataAffiliateAgreements are included in the audit."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        member_agreement = factories.MemberAgreementFactory.create()
        non_data_affiliate_agreement = factories.NonDataAffiliateAgreementFactory.create()
        audit = uploader_audit.UploaderAudit()
        self.assertEqual(audit.queryset.count(), 1)
        self.assertIn(data_affiliate_agreement, audit.queryset)
        self.assertNotIn(member_agreement, audit.queryset)
        self.assertNotIn(non_data_affiliate_agreement, audit.queryset)
