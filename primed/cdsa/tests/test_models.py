"""Tests of models in the `cdsa` app."""

from datetime import datetime

from anvil_consortium_manager.models import ManagedGroup
from anvil_consortium_manager.tests.factories import (
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
    WorkspaceFactory,
)
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import TestCase, override_settings

from primed.duo.tests.factories import DataUseModifierFactory, DataUsePermissionFactory
from primed.primed_anvil.tests.factories import (
    AvailableDataFactory,
    StudyFactory,
    StudySiteFactory,
)
from primed.users.tests.factories import UserFactory

from .. import models
from . import factories


class AgreementMajorVersionTest(TestCase):
    """Tests for the AgreementMajorVersion model."""

    def test_model_saving(self):
        instance = models.AgreementMajorVersion(version=1)
        instance.save()
        self.assertIsInstance(instance, models.AgreementMajorVersion)

    def test_is_valid_default(self):
        instance = factories.AgreementMajorVersionFactory.create()
        self.assertTrue(instance.is_valid)

    def test_unique(self):
        factories.AgreementMajorVersionFactory.create(version=1)
        instance = factories.AgreementMajorVersionFactory.build(version=1)
        with self.assertRaisesMessage(ValidationError, "already exists"):
            instance.full_clean()
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_version_zero(self):
        """ValidationError raised when version is zero."""
        instance = factories.AgreementMajorVersionFactory.build(version=0)
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("version", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["version"]), 1)
        self.assertIn("greater than or equal to", e.exception.message_dict["version"][0])

    def test_version_negative(self):
        """ValidationError raised when version is negative."""
        instance = factories.AgreementMajorVersionFactory.build(version=-1)
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("version", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["version"]), 1)
        self.assertIn("greater than or equal to", e.exception.message_dict["version"][0])

    def test_str(self):
        """__str__ method works as expected."""
        instance = factories.AgreementMajorVersionFactory.build()
        self.assertIsInstance(str(instance), str)

    def test_get_absolute_url(self):
        """get_absolute_url method works correctly."""
        instance = factories.AgreementMajorVersionFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)


class AgreementVersionTest(TestCase):
    """Tests for the AgreementVersion model."""

    def test_model_saving(self):
        major_version = factories.AgreementMajorVersionFactory.create()
        instance = models.AgreementVersion(major_version=major_version, minor_version=0, date_approved=datetime.today())
        instance.save()
        self.assertIsInstance(instance, models.AgreementVersion)

    def test_unique(self):
        major_version = factories.AgreementMajorVersionFactory.create()
        factories.AgreementVersionFactory.create(major_version=major_version, minor_version=0)
        instance = factories.AgreementVersionFactory.build(major_version=major_version, minor_version=0)
        with self.assertRaisesMessage(ValidationError, "already exists"):
            instance.full_clean()
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_minor_version_zero(self):
        """full_clean raises no exception when minor_version is zero."""
        major_version = factories.AgreementMajorVersionFactory.create()
        instance = factories.AgreementVersionFactory.build(major_version=major_version, minor_version=0)
        instance.full_clean()

    def test_minor_version_negative(self):
        """ValidationError raised when minor_version is negative."""
        major_version = factories.AgreementMajorVersionFactory.create()
        instance = factories.AgreementVersionFactory.build(major_version=major_version, minor_version=-1)
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("minor_version", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["minor_version"]), 1)
        self.assertIn("greater than or equal to", e.exception.message_dict["minor_version"][0])

    def test_full_version(self):
        """full_version property works as expected."""
        self.assertEqual(
            factories.AgreementVersionFactory(major_version__version=1, minor_version=0).full_version,
            "v1.0",
        )
        self.assertEqual(
            factories.AgreementVersionFactory(major_version__version=1, minor_version=5).full_version,
            "v1.5",
        )
        self.assertEqual(
            factories.AgreementVersionFactory(major_version__version=1, minor_version=10).full_version,
            "v1.10",
        )
        self.assertEqual(
            factories.AgreementVersionFactory(major_version__version=2, minor_version=3).full_version,
            "v2.3",
        )

    def test_str(self):
        """__str__ method works as expected."""
        instance = factories.AgreementVersionFactory.build()
        self.assertIsInstance(str(instance), str)

    def test_get_absolute_url(self):
        """get_absolute_url method works correctly."""
        instance = factories.AgreementVersionFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)


class SignedAgreementTest(TestCase):
    """Tests for the SignedAgreement model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        agreement_version = factories.AgreementVersionFactory.create()
        user = UserFactory.create()
        group = ManagedGroupFactory.create()
        instance = models.SignedAgreement(
            cc_id=1001,
            representative=user,
            representative_role="foo",
            signing_institution="bar",
            type=models.SignedAgreement.MEMBER,
            version=agreement_version,
            anvil_access_group=group,
        )
        instance.save()
        self.assertIsInstance(instance, models.SignedAgreement)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.SignedAgreementFactory.create(
            cc_id=1234,
        )
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "1234")

    def test_get_absolute_url(self):
        """get_absolute_url method works correctly."""
        instance = factories.MemberAgreementFactory.create()
        self.assertEqual(instance.signed_agreement.get_absolute_url(), instance.get_absolute_url())
        instance = factories.DataAffiliateAgreementFactory.create()
        self.assertEqual(instance.signed_agreement.get_absolute_url(), instance.get_absolute_url())
        instance = factories.NonDataAffiliateAgreementFactory.create()
        self.assertEqual(instance.signed_agreement.get_absolute_url(), instance.get_absolute_url())

    def test_member_choices(self):
        """Can create instances with all of the member choices."""
        instance = factories.SignedAgreementFactory.create(type=models.SignedAgreement.MEMBER)
        self.assertEqual(instance.type, models.SignedAgreement.MEMBER)
        instance = factories.SignedAgreementFactory.create(type=models.SignedAgreement.DATA_AFFILIATE)
        self.assertEqual(instance.type, models.SignedAgreement.DATA_AFFILIATE)
        instance = factories.SignedAgreementFactory.create(type=models.SignedAgreement.NON_DATA_AFFILIATE)
        self.assertEqual(instance.type, models.SignedAgreement.NON_DATA_AFFILIATE)

    def test_unique_cc_id(self):
        """Saving a duplicate model fails."""
        obj = factories.SignedAgreementFactory.create()
        user = UserFactory.create()
        group = ManagedGroupFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        instance = factories.SignedAgreementFactory.build(
            #            study=study,
            cc_id=obj.cc_id,
            representative=user,
            anvil_access_group=group,
            version=agreement_version,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("cc_id", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["cc_id"]), 1)
        self.assertIn("already exists", e.exception.message_dict["cc_id"][0])
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_cc_id_zero(self):
        """ValidationError raised when cc_id is zero."""
        user = UserFactory.create()
        group = ManagedGroupFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        instance = factories.SignedAgreementFactory.build(
            cc_id=0,
            representative=user,
            anvil_access_group=group,
            version=agreement_version,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("cc_id", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["cc_id"]), 1)
        self.assertIn("greater than or equal to", e.exception.message_dict["cc_id"][0])

    def test_cc_id_negative(self):
        """ValidationError raised when cc_id is negative."""
        user = UserFactory.create()
        group = ManagedGroupFactory.create()
        agreement_version = factories.AgreementVersionFactory.create()
        instance = factories.SignedAgreementFactory.build(
            cc_id=-1,
            representative=user,
            anvil_access_group=group,
            version=agreement_version,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("cc_id", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["cc_id"]), 1)
        self.assertIn("greater than or equal to", e.exception.message_dict["cc_id"][0])

    def test_agreement_version_protect(self):
        """An AgreementVersion cannot be deleted if there are associated SignedAgreements."""
        agreement_version = factories.AgreementVersionFactory.create()
        factories.SignedAgreementFactory.create(version=agreement_version)
        with self.assertRaises(ProtectedError):
            agreement_version.delete()

    def test_status_field(self):
        # default
        instance = factories.SignedAgreementFactory.create()
        self.assertEqual(instance.status, instance.StatusChoices.ACTIVE)
        instance.full_clean()
        # other choices
        instance = factories.SignedAgreementFactory.create(status=models.SignedAgreement.StatusChoices.WITHDRAWN)
        self.assertEqual(instance.status, instance.StatusChoices.WITHDRAWN)
        instance.full_clean()
        instance = factories.SignedAgreementFactory.create(status=models.SignedAgreement.StatusChoices.LAPSED)
        self.assertEqual(instance.status, instance.StatusChoices.LAPSED)
        instance.full_clean()
        instance = factories.SignedAgreementFactory.create(status=models.SignedAgreement.StatusChoices.REPLACED)
        self.assertEqual(instance.status, instance.StatusChoices.REPLACED)
        instance.full_clean()

        # not allowed
        instance = factories.SignedAgreementFactory.create(status="foo")
        with self.assertRaises(ValidationError):
            instance.full_clean()

    def test_can_add_accessors(self):
        """Saving a model with accessors set is valid."""
        accessors = UserFactory.create_batch(2)
        instance = factories.MemberAgreementFactory.create()
        instance.signed_agreement.accessors.add(*accessors)
        self.assertIn(accessors[0], instance.signed_agreement.accessors.all())
        self.assertIn(accessors[1], instance.signed_agreement.accessors.all())

    def test_get_combined_type(self):
        obj = factories.MemberAgreementFactory()
        self.assertEqual(obj.signed_agreement.combined_type, "Member")
        obj = factories.MemberAgreementFactory(is_primary=False)
        self.assertEqual(obj.signed_agreement.combined_type, "Member component")
        obj = factories.DataAffiliateAgreementFactory()
        self.assertEqual(obj.signed_agreement.combined_type, "Data affiliate")
        obj = factories.DataAffiliateAgreementFactory(is_primary=False)
        self.assertEqual(obj.signed_agreement.combined_type, "Data affiliate component")
        obj = factories.NonDataAffiliateAgreementFactory()
        self.assertEqual(obj.signed_agreement.combined_type, "Non-data affiliate")

    def test_get_agreement_type(self):
        obj = factories.MemberAgreementFactory()
        self.assertEqual(obj.signed_agreement.get_agreement_type(), obj)
        obj = factories.DataAffiliateAgreementFactory()
        self.assertEqual(obj.signed_agreement.get_agreement_type(), obj)
        obj = factories.NonDataAffiliateAgreementFactory()
        self.assertEqual(obj.signed_agreement.get_agreement_type(), obj)

    def test_get_agreement_group(self):
        obj = factories.MemberAgreementFactory()
        self.assertEqual(obj.signed_agreement.agreement_group, obj.study_site)
        obj = factories.DataAffiliateAgreementFactory()
        self.assertEqual(obj.signed_agreement.agreement_group, obj.study)
        obj = factories.NonDataAffiliateAgreementFactory()
        self.assertEqual(obj.signed_agreement.agreement_group, obj.affiliation)

    def test_is_in_cdsa_group(self):
        """is_in_cdsa_group works as expected."""
        obj = factories.SignedAgreementFactory.create()
        # When group does not exist
        with self.assertRaises(ManagedGroup.DoesNotExist):
            obj.is_in_cdsa_group()
        # Create group, without adding agreement
        cdsa_group = ManagedGroupFactory.create(name="TEST_PRIMED_CDSA")
        self.assertFalse(obj.is_in_cdsa_group())
        # Add agreement and check again,
        GroupGroupMembershipFactory.create(parent_group=cdsa_group, child_group=obj.anvil_access_group)
        self.assertTrue(obj.is_in_cdsa_group())

    @override_settings(ANVIL_CDSA_GROUP_NAME="FOO")
    def test_is_in_cdsa_group_different_group_name(self):
        """is_in_cdsa_group works as expected."""
        obj = factories.SignedAgreementFactory.create()
        # When group does not exist
        with self.assertRaises(ManagedGroup.DoesNotExist):
            obj.is_in_cdsa_group()
        # Create group, without adding agreement
        cdsa_group = ManagedGroupFactory.create(name="FOO")
        self.assertFalse(obj.is_in_cdsa_group())
        # Add agreement and check again,
        GroupGroupMembershipFactory.create(parent_group=cdsa_group, child_group=obj.anvil_access_group)
        self.assertTrue(obj.is_in_cdsa_group())


class MemberAgreementTest(TestCase):
    """Tests for the MemberAgremeent model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        signed_agreement = factories.SignedAgreementFactory.create(type=models.SignedAgreement.MEMBER)
        study_site = StudySiteFactory.create()
        instance = models.MemberAgreement(
            signed_agreement=signed_agreement,
            study_site=study_site,
            is_primary=True,
        )
        instance.save()
        self.assertIsInstance(instance, models.MemberAgreement)

    def test_is_primary(self):
        """Creation using the model constructor and .save() works."""
        instance = factories.MemberAgreementFactory.create(is_primary=True)
        self.assertEqual(instance.is_primary, True)
        instance = factories.MemberAgreementFactory.create(is_primary=False)
        self.assertEqual(instance.is_primary, False)

    def test_clean_incorrect_type(self):
        signed_agreement = factories.SignedAgreementFactory.create(type=models.SignedAgreement.DATA_AFFILIATE)
        instance = factories.MemberAgreementFactory.build(signed_agreement=signed_agreement)
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("signed_agreement", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["signed_agreement"]), 1)
        self.assertEqual(
            models.MemberAgreement.ERROR_TYPE_DOES_NOT_MATCH,
            e.exception.error_dict["signed_agreement"][0].messages[0],
        )

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.MemberAgreementFactory.create()
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), str(instance.signed_agreement))

    def test_get_absolute_url(self):
        """get_absolute_url method works correctly."""
        instance = factories.MemberAgreementFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)

    def test_error_duplicate_signed_agreement(self):
        """Cannot link two member agreements to one signed_agreement."""
        instance_1 = factories.MemberAgreementFactory.create()
        study_site = StudySiteFactory.create()
        instance_2 = factories.MemberAgreementFactory.build(
            signed_agreement=instance_1.signed_agreement,
            study_site=study_site,
        )
        with self.assertRaises(ValidationError) as e:
            instance_2.full_clean()
        self.assertIn("signed_agreement", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["signed_agreement"]), 1)
        self.assertIn("already exists", e.exception.error_dict["signed_agreement"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance_2.save()

    def test_get_agreement_group(self):
        instance = factories.MemberAgreementFactory.create()
        self.assertEqual(instance.get_agreement_group(), instance.study_site)


class DataAffiliateAgreementTest(TestCase):
    """Tests for the DataAffiliateAgreement model."""

    def test_defaults(self):
        upload_group = ManagedGroupFactory.create()
        signed_agreement = factories.SignedAgreementFactory.create(type=models.SignedAgreement.DATA_AFFILIATE)
        study = StudyFactory.create()
        instance = models.DataAffiliateAgreement(
            signed_agreement=signed_agreement,
            study=study,
            anvil_upload_group=upload_group,
        )
        self.assertFalse(instance.requires_study_review)
        self.assertEqual(instance.additional_limitations, "")

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        upload_group = ManagedGroupFactory.create()
        signed_agreement = factories.SignedAgreementFactory.create(type=models.SignedAgreement.DATA_AFFILIATE)
        study = StudyFactory.create()
        instance = models.DataAffiliateAgreement(
            signed_agreement=signed_agreement,
            study=study,
            anvil_upload_group=upload_group,
            is_primary=True,
        )
        instance.save()
        self.assertIsInstance(instance, models.DataAffiliateAgreement)

    def test_is_primary(self):
        """Creation using the model constructor and .save() works."""
        instance = factories.DataAffiliateAgreementFactory.create(is_primary=True)
        self.assertEqual(instance.is_primary, True)
        instance = factories.DataAffiliateAgreementFactory.create(is_primary=False)
        self.assertEqual(instance.is_primary, False)

    def test_can_add_uploaders(self):
        """Saving a model with uploaders set is valid."""
        uploaders = UserFactory.create_batch(2)
        instance = factories.DataAffiliateAgreementFactory.create()
        instance.uploaders.add(*uploaders)
        self.assertIn(uploaders[0], instance.uploaders.all())
        self.assertIn(uploaders[1], instance.uploaders.all())

    def test_clean_incorrect_type(self):
        signed_agreement = factories.SignedAgreementFactory.create(type=models.SignedAgreement.MEMBER)
        study = StudyFactory.create()
        upload_group = ManagedGroupFactory.create()
        instance = factories.DataAffiliateAgreementFactory.build(
            signed_agreement=signed_agreement,
            study=study,
            anvil_upload_group=upload_group,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("signed_agreement", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["signed_agreement"]), 1)
        self.assertEqual(
            models.DataAffiliateAgreement.ERROR_TYPE_DOES_NOT_MATCH,
            e.exception.error_dict["signed_agreement"][0].messages[0],
        )

    def test_clean_additional_limitations_primary(self):
        instance = factories.DataAffiliateAgreementFactory.create(
            is_primary=True,
            additional_limitations="foo bar",
        )
        instance.full_clean()

    def test_clean_additional_limitations_not_primary(self):
        instance = factories.DataAffiliateAgreementFactory.create(
            is_primary=False,
            additional_limitations="foo bar",
        )
        with self.assertRaises(ValidationError) as e:
            instance.clean()
        self.assertEqual(len(e.exception.error_dict), 1)
        self.assertIn("additional_limitations", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["additional_limitations"]), 1)
        self.assertIn(
            "only allowed for primary agreements",
            e.exception.error_dict["additional_limitations"][0].message,
        )

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.DataAffiliateAgreementFactory.create()
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), str(instance.signed_agreement))

    def test_get_absolute_url(self):
        """get_absolute_url method works correctly."""
        instance = factories.DataAffiliateAgreementFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)

    def test_error_duplicate_signed_agreement(self):
        """Cannot link two member agreements to one signed_agreement."""
        instance_1 = factories.DataAffiliateAgreementFactory.create()
        study = StudyFactory.create()
        upload_group = ManagedGroupFactory.create()
        instance_2 = factories.DataAffiliateAgreementFactory.build(
            signed_agreement=instance_1.signed_agreement,
            study=study,
            anvil_upload_group=upload_group,
        )
        with self.assertRaises(ValidationError) as e:
            instance_2.full_clean()
        self.assertIn("signed_agreement", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["signed_agreement"]), 1)
        self.assertIn("already exists", e.exception.error_dict["signed_agreement"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance_2.save()

    def test_get_agreement_group(self):
        instance = factories.DataAffiliateAgreementFactory.create()
        self.assertEqual(instance.get_agreement_group(), instance.study)

    def test_requires_study_review_primary(self):
        """Can set requires_study_review"""
        instance = factories.DataAffiliateAgreementFactory.create(requires_study_review=True)
        self.assertTrue(instance.requires_study_review)

    def test_requires_study_review_not_primary(self):
        """ValidationError when trying to set requires_study_review=True for components."""
        instance = factories.DataAffiliateAgreementFactory.create(
            is_primary=False,
            requires_study_review=True,
        )
        with self.assertRaises(ValidationError) as e:
            instance.clean()
        self.assertEqual(len(e.exception.error_dict), 1)
        self.assertIn("requires_study_review", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["requires_study_review"]), 1)
        self.assertIn(
            "can only be True for primary",
            e.exception.error_dict["requires_study_review"][0].message,
        )


class NonDataAffiliateAgreementTest(TestCase):
    """Tests for the NonDataAffiliateAgreement model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        signed_agreement = factories.SignedAgreementFactory.create(type=models.SignedAgreement.NON_DATA_AFFILIATE)
        instance = models.NonDataAffiliateAgreement(
            signed_agreement=signed_agreement,
            affiliation="Foo",
        )
        instance.save()
        self.assertIsInstance(instance, models.NonDataAffiliateAgreement)

    def test_clean_incorrect_type(self):
        signed_agreement = factories.SignedAgreementFactory.create(type=models.SignedAgreement.MEMBER)
        instance = factories.NonDataAffiliateAgreementFactory.build(
            signed_agreement=signed_agreement,
            affiliation="Foo Bar",
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("signed_agreement", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["signed_agreement"]), 1)
        self.assertEqual(
            models.NonDataAffiliateAgreement.ERROR_TYPE_DOES_NOT_MATCH,
            e.exception.error_dict["signed_agreement"][0].messages[0],
        )

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.NonDataAffiliateAgreementFactory.create()
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), str(instance.signed_agreement))

    def test_get_absolute_url(self):
        """get_absolute_url method works correctly."""
        instance = factories.NonDataAffiliateAgreementFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)

    def test_error_duplicate_signed_agreement(self):
        """Cannot link two member agreements to one signed_agreement."""
        instance_1 = factories.NonDataAffiliateAgreementFactory.create()
        instance_2 = factories.NonDataAffiliateAgreementFactory.build(
            signed_agreement=instance_1.signed_agreement, affiliation="Foo"
        )
        with self.assertRaises(ValidationError) as e:
            instance_2.full_clean()
        self.assertIn("signed_agreement", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["signed_agreement"]), 1)
        self.assertIn("already exists", e.exception.error_dict["signed_agreement"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance_2.save()

    def test_get_agreement_group(self):
        instance = factories.NonDataAffiliateAgreementFactory.create()
        self.assertEqual(instance.get_agreement_group(), instance.affiliation)


class CDSAWorkspaceTest(TestCase):
    """Tests for the CDSA workspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        study = StudyFactory.create()
        requester = UserFactory.create()
        instance = models.CDSAWorkspace(
            study=study,
            acknowledgments="test acknowledgments",
            requested_by=requester,
            workspace=workspace,
            gsr_restricted=False,
        )
        instance.save()
        self.assertIsInstance(instance, models.CDSAWorkspace)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.CDSAWorkspaceFactory.create()
        self.assertIsInstance(instance.__str__(), str)

    def test_can_add_data_use_modifiers(self):
        """Saving a model with data_use_permission and data_use_modifiers set is valid."""
        data_use_permission = DataUsePermissionFactory.create()
        data_use_modifiers = DataUseModifierFactory.create_batch(2)
        instance = factories.CDSAWorkspaceFactory.create(
            data_use_permission=data_use_permission,
        )
        instance.data_use_modifiers.add(*data_use_modifiers)
        self.assertIn(data_use_modifiers[0], instance.data_use_modifiers.all())
        self.assertIn(data_use_modifiers[1], instance.data_use_modifiers.all())

    def test_study_protect(self):
        """Cannot delete a Study if it has an associated CDSAWorkspace."""
        study = factories.StudyFactory.create()
        factories.CDSAWorkspaceFactory.create(
            study=study,
        )
        with self.assertRaises(ProtectedError):
            study.delete()

    def test_available_data(self):
        """Can add available data to a workspace."""
        available_data = AvailableDataFactory.create_batch(2)
        instance = factories.CDSAWorkspaceFactory.create()
        instance.available_data.add(*available_data)
        self.assertIn(available_data[0], instance.available_data.all())
        self.assertIn(available_data[1], instance.available_data.all())

    def test_additional_limitations(self):
        """Can have additional_limitations set."""
        instance = factories.CDSAWorkspaceFactory.create(additional_limitations="foo")
        self.assertEqual(instance.additional_limitations, "foo")

    def test_get_primary_cdsa(self):
        """get_primary_cdsa returns the primary valid CDSA for the study."""
        instance = factories.CDSAWorkspaceFactory.create()
        agreement = factories.DataAffiliateAgreementFactory.create(
            is_primary=True,
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
            study=instance.study,
        )
        self.assertEqual(instance.get_primary_cdsa(), agreement)

    def test_get_primary_cdsa_not_primary(self):
        instance = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            is_primary=False,
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
            study=instance.study,
        )
        with self.assertRaises(models.DataAffiliateAgreement.DoesNotExist):
            instance.get_primary_cdsa()

    def test_get_primary_cdsa_not_active(self):
        instance = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            is_primary=True,
            signed_agreement__status=models.SignedAgreement.StatusChoices.LAPSED,
            study=instance.study,
        )
        with self.assertRaises(models.DataAffiliateAgreement.DoesNotExist):
            instance.get_primary_cdsa()

    def test_get_primary_cdsa_different_study(self):
        instance = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            is_primary=True,
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
            # study=instance.study,
        )
        with self.assertRaises(models.DataAffiliateAgreement.DoesNotExist):
            instance.get_primary_cdsa()

    def test_get_primary_cdsa_multiple_agreements(self):
        """get_primary_cdsa returns the primary valid CDSA for the study."""
        instance = factories.CDSAWorkspaceFactory.create()
        factories.DataAffiliateAgreementFactory.create(
            is_primary=True,
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
            study=instance.study,
        )
        factories.DataAffiliateAgreementFactory.create(
            is_primary=True,
            signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
            study=instance.study,
        )
        with self.assertRaises(models.DataAffiliateAgreement.MultipleObjectsReturned):
            instance.get_primary_cdsa()
