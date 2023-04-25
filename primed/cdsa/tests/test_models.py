"""Tests of models in the `cdsa` app."""

from datetime import datetime

from anvil_consortium_manager.tests.factories import ManagedGroupFactory
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import TestCase

from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory
from primed.users.tests.factories import UserFactory

from .. import models
from . import factories


class AgreementVersionTest(TestCase):
    """Tests for the AgreementVersion model."""

    def test_model_saving(self):
        instance = models.AgreementVersion(
            major_version=1, minor_version=0, date_approved=datetime.today()
        )
        instance.save()
        self.assertIsInstance(instance, models.AgreementVersion)

    def test_unique(self):
        factories.AgreementVersionFactory.create(major_version=1, minor_version=0)
        instance = factories.AgreementVersionFactory.build(
            major_version=1, minor_version=0
        )
        with self.assertRaisesMessage(ValidationError, "already exists"):
            instance.full_clean()
        with self.assertRaisesMessage(IntegrityError, "UNIQUE"):
            instance.save()

    def test_major_version_zero(self):
        """ValidationError raised when major_version is zero."""
        instance = factories.AgreementVersionFactory.build(major_version=0)
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("major_version", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["major_version"]), 1)
        self.assertIn(
            "greater than or equal to", e.exception.message_dict["major_version"][0]
        )

    def test_major_version_negative(self):
        """ValidationError raised when major_version is negative."""
        instance = factories.AgreementVersionFactory.build(major_version=-1)
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("major_version", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["major_version"]), 1)
        self.assertIn(
            "greater than or equal to", e.exception.message_dict["major_version"][0]
        )

    def test_minor_version_zero(self):
        """full_clean raises no exception when minor_version is zero."""
        instance = factories.AgreementVersionFactory.build(minor_version=0)
        instance.full_clean()

    def test_minor_version_negative(self):
        """ValidationError raised when minor_version is negative."""
        instance = factories.AgreementVersionFactory.build(minor_version=-1)
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("minor_version", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["minor_version"]), 1)
        self.assertIn(
            "greater than or equal to", e.exception.message_dict["minor_version"][0]
        )

    def test_full_version(self):
        """full_version property works as expected."""
        self.assertEqual(
            factories.AgreementVersionFactory(
                major_version=1, minor_version=0
            ).full_version,
            "1.0",
        )
        self.assertEqual(
            factories.AgreementVersionFactory(
                major_version=1, minor_version=5
            ).full_version,
            "1.5",
        )
        self.assertEqual(
            factories.AgreementVersionFactory(
                major_version=1, minor_version=10
            ).full_version,
            "1.10",
        )
        self.assertEqual(
            factories.AgreementVersionFactory(
                major_version=2, minor_version=3
            ).full_version,
            "2.3",
        )

    def test_str(self):
        """__str__ method works as expected."""
        instance = factories.AgreementVersionFactory.build()
        self.assertIsInstance(str(instance), str)


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
            is_primary=True,
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
        self.assertEqual(
            instance.signed_agreement.get_absolute_url(), instance.get_absolute_url()
        )
        instance = factories.DataAffiliateAgreementFactory.create()
        self.assertEqual(
            instance.signed_agreement.get_absolute_url(), instance.get_absolute_url()
        )
        instance = factories.NonDataAffiliateAgreementFactory.create()
        self.assertEqual(
            instance.signed_agreement.get_absolute_url(), instance.get_absolute_url()
        )

    def test_member_choices(self):
        """Can create instances with all of the member choices."""
        instance = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER
        )
        self.assertEqual(instance.type, models.SignedAgreement.MEMBER)
        instance = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.DATA_AFFILIATE
        )
        self.assertEqual(instance.type, models.SignedAgreement.DATA_AFFILIATE)
        instance = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.NON_DATA_AFFILIATE
        )
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

    def test_agreement_version_protect(self):
        """An AgreementVersion cannot be deleted if there are associated SignedAgreements."""
        agreement_version = factories.AgreementVersionFactory.create()
        factories.SignedAgreementFactory.create(version=agreement_version)
        with self.assertRaises(ProtectedError):
            agreement_version.delete()

    def test_get_combined_type(self):
        obj = factories.MemberAgreementFactory()
        self.assertEqual(obj.signed_agreement.combined_type, "Member")
        obj = factories.MemberAgreementFactory(signed_agreement__is_primary=False)
        self.assertEqual(obj.signed_agreement.combined_type, "Member component")
        obj = factories.DataAffiliateAgreementFactory()
        self.assertEqual(obj.signed_agreement.combined_type, "Data affiliate")
        obj = factories.DataAffiliateAgreementFactory(
            signed_agreement__is_primary=False
        )
        self.assertEqual(obj.signed_agreement.combined_type, "Data affiliate component")
        obj = factories.NonDataAffiliateAgreementFactory()
        self.assertEqual(obj.signed_agreement.combined_type, "Non-data affiliate")
        obj = factories.NonDataAffiliateAgreementFactory(
            signed_agreement__is_primary=False
        )
        self.assertEqual(
            obj.signed_agreement.combined_type, "Non-data affiliate component"
        )


class MemberAgreementTest(TestCase):
    """Tests for the MemberAgremeent model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER
        )
        study_site = StudySiteFactory.create()
        instance = models.MemberAgreement(
            signed_agreement=signed_agreement,
            study_site=study_site,
        )
        instance.save()
        self.assertIsInstance(instance, models.MemberAgreement)

    def test_clean_incorrect_type(self):
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.DATA_AFFILIATE
        )
        instance = factories.MemberAgreementFactory.build(
            signed_agreement=signed_agreement
        )
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
        self.assertIn(
            "already exists", e.exception.error_dict["signed_agreement"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance_2.save()


class DataAffiliateAgreementTest(TestCase):
    """Tests for the DataAffiliateAgreement model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        upload_group = ManagedGroupFactory.create()
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.DATA_AFFILIATE
        )
        study = StudyFactory.create()
        instance = models.DataAffiliateAgreement(
            signed_agreement=signed_agreement,
            study=study,
            anvil_upload_group=upload_group,
        )
        instance.save()
        self.assertIsInstance(instance, models.DataAffiliateAgreement)

    def test_clean_incorrect_type(self):
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER
        )
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
        self.assertIn(
            "already exists", e.exception.error_dict["signed_agreement"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance_2.save()


class NonDataAffiliateAgreementTest(TestCase):
    """Tests for the NonDataAffiliateAgreement model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.NON_DATA_AFFILIATE
        )
        instance = models.NonDataAffiliateAgreement(
            signed_agreement=signed_agreement,
            affiliation="Foo",
        )
        instance.save()
        self.assertIsInstance(instance, models.NonDataAffiliateAgreement)

    def test_clean_incorrect_type(self):
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER
        )
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
        self.assertIn(
            "already exists", e.exception.error_dict["signed_agreement"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance_2.save()
