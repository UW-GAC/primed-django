"""Tests of models in the `cdsa` app."""

from anvil_consortium_manager.tests.factories import ManagedGroupFactory
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase

from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory
from primed.users.tests.factories import UserFactory

from .. import models
from . import factories


class SignedAgreementTest(TestCase):
    """Tests for the SignedAgreement model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        user = UserFactory.create()
        group = ManagedGroupFactory.create()
        instance = models.SignedAgreement(
            cc_id=1001,
            representative=user,
            representative_role="foo",
            institution="bar",
            type=models.SignedAgreement.MEMBER,
            version=1,
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

    # def test_get_absolute_url(self):
    #     """get_absolute_url method works correctly."""
    #     instance = factories.dbGaPStudyAccessionFactory.create()
    #     self.assertIsInstance(instance.get_absolute_url(), str)

    def test_member_choices(self):
        """Can create instances with all of the member choices."""
        instance = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER
        )
        self.assertEqual(instance.type, models.SignedAgreement.MEMBER)
        instance = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER_COMPONENT
        )
        self.assertEqual(instance.type, models.SignedAgreement.MEMBER_COMPONENT)
        instance = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.DATA_AFFILIATE
        )
        self.assertEqual(instance.type, models.SignedAgreement.DATA_AFFILIATE)
        instance = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.DATA_AFFILIATE_COMPONENT
        )
        self.assertEqual(instance.type, models.SignedAgreement.DATA_AFFILIATE_COMPONENT)
        instance = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.NON_DATA_AFFILIATE
        )
        self.assertEqual(instance.type, models.SignedAgreement.NON_DATA_AFFILIATE)
        instance = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.NON_DATA_AFFILIATE_COMPONENT
        )
        self.assertEqual(
            instance.type, models.SignedAgreement.NON_DATA_AFFILIATE_COMPONENT
        )

    def test_unique_cc_id(self):
        """Saving a duplicate model fails."""
        obj = factories.SignedAgreementFactory.create()
        user = UserFactory.create()
        group = ManagedGroupFactory.create()
        instance = factories.SignedAgreementFactory.build(
            #            study=study,
            cc_id=obj.cc_id,
            representative=user,
            anvil_access_group=group,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("cc_id", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["cc_id"]), 1)
        self.assertIn("already exists", e.exception.error_dict["cc_id"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance.save()


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
            type=models.SignedAgreement.MEMBER_COMPONENT
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


class MemberComponentAgreementTest(TestCase):
    """Tests for the MemberComponentAgremeent model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        member_agreement = factories.MemberAgreementFactory.create()
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER_COMPONENT
        )
        instance = models.MemberComponentAgreement(
            signed_agreement=signed_agreement,
            component_of=member_agreement,
        )
        instance.save()
        self.assertIsInstance(instance, models.MemberComponentAgreement)

    def test_clean_incorrect_type(self):
        member_agreement = factories.MemberAgreementFactory.create()
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER
        )
        instance = factories.MemberComponentAgreementFactory.build(
            signed_agreement=signed_agreement, component_of=member_agreement
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("signed_agreement", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["signed_agreement"]), 1)
        self.assertEqual(
            models.MemberComponentAgreement.ERROR_TYPE_DOES_NOT_MATCH,
            e.exception.error_dict["signed_agreement"][0].messages[0],
        )

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.MemberComponentAgreementFactory.create()
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), str(instance.signed_agreement))

    def test_error_duplicate_signed_agreement(self):
        """Cannot link two member agreements to one signed_agreement."""
        instance_1 = factories.MemberComponentAgreementFactory.create()
        primary = factories.MemberAgreementFactory.create()
        instance_2 = factories.MemberComponentAgreementFactory.build(
            signed_agreement=instance_1.signed_agreement, component_of=primary
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

    def test_component_of_protect(self):
        """A MemberComponentAgreement is deleted if its component_of is deleted."""
        member_agreement = factories.MemberAgreementFactory.create()
        component = factories.MemberComponentAgreementFactory.create(
            component_of=member_agreement
        )
        member_agreement.delete()
        with self.assertRaises(models.MemberComponentAgreement.DoesNotExist):
            component.refresh_from_db()


class DataAffiliateAgreementTest(TestCase):
    """Tests for the DataAffiliateAgreement model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.DATA_AFFILIATE
        )
        study = StudyFactory.create()
        instance = models.DataAffiliateAgreement(
            signed_agreement=signed_agreement,
            study=study,
        )
        instance.save()
        self.assertIsInstance(instance, models.DataAffiliateAgreement)

    def test_clean_incorrect_type(self):
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.DATA_AFFILIATE_COMPONENT
        )
        study = StudyFactory.create()
        instance = factories.DataAffiliateAgreementFactory.build(
            signed_agreement=signed_agreement,
            study=study,
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

    def test_error_duplicate_signed_agreement(self):
        """Cannot link two member agreements to one signed_agreement."""
        instance_1 = factories.DataAffiliateAgreementFactory.create()
        study = StudyFactory.create()
        instance_2 = factories.DataAffiliateAgreementFactory.build(
            signed_agreement=instance_1.signed_agreement,
            study=study,
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


class DataAffiliateComponentAgreementTest(TestCase):
    """Tests for the DataAffiliateAgreement model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.DATA_AFFILIATE_COMPONENT
        )
        instance = models.DataAffiliateComponentAgreement(
            signed_agreement=signed_agreement,
            component_of=data_affiliate_agreement,
        )
        instance.save()
        self.assertIsInstance(instance, models.DataAffiliateComponentAgreement)

    def test_clean_incorrect_type(self):
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.DATA_AFFILIATE
        )
        instance = factories.DataAffiliateComponentAgreementFactory.build(
            signed_agreement=signed_agreement, component_of=data_affiliate_agreement
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("signed_agreement", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["signed_agreement"]), 1)
        self.assertEqual(
            models.DataAffiliateComponentAgreement.ERROR_TYPE_DOES_NOT_MATCH,
            e.exception.error_dict["signed_agreement"][0].messages[0],
        )

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.DataAffiliateComponentAgreementFactory.create()
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), str(instance.signed_agreement))

    def test_error_duplicate_signed_agreement(self):
        """Cannot link two member agreements to one signed_agreement."""
        instance_1 = factories.DataAffiliateComponentAgreementFactory.create()
        primary = factories.DataAffiliateAgreementFactory.create()
        instance_2 = factories.DataAffiliateComponentAgreementFactory.build(
            signed_agreement=instance_1.signed_agreement, component_of=primary
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

    def test_component_of_protect(self):
        """A DataAffiliateComponentAgreement is deleted if its component_of is deleted."""
        data_affiliate_agreement = factories.DataAffiliateAgreementFactory.create()
        component = factories.DataAffiliateComponentAgreementFactory.create(
            component_of=data_affiliate_agreement
        )
        data_affiliate_agreement.delete()
        with self.assertRaises(models.DataAffiliateComponentAgreement.DoesNotExist):
            component.refresh_from_db()


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
            type=models.SignedAgreement.NON_DATA_AFFILIATE_COMPONENT
        )
        instance = factories.NonDataAffiliateAgreementFactory.build(
            signed_agreement=signed_agreement,
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

    def test_error_duplicate_signed_agreement(self):
        """Cannot link two member agreements to one signed_agreement."""
        instance_1 = factories.NonDataAffiliateAgreementFactory.create()
        instance_2 = factories.NonDataAffiliateAgreementFactory.build(
            signed_agreement=instance_1.signed_agreement,
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


class NonDataAffiliateComponentAgreementTest(TestCase):
    """Tests for the NonDataAffiliateAgreement model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        data_affiliate_agreement = factories.NonDataAffiliateAgreementFactory.create()
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.NON_DATA_AFFILIATE_COMPONENT
        )
        instance = models.NonDataAffiliateComponentAgreement(
            signed_agreement=signed_agreement,
            component_of=data_affiliate_agreement,
        )
        instance.save()
        self.assertIsInstance(instance, models.NonDataAffiliateComponentAgreement)

    def test_clean_incorrect_type(self):
        data_affiliate_agreement = factories.NonDataAffiliateAgreementFactory.create()
        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.NON_DATA_AFFILIATE
        )
        instance = factories.NonDataAffiliateComponentAgreementFactory.build(
            signed_agreement=signed_agreement, component_of=data_affiliate_agreement
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("signed_agreement", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["signed_agreement"]), 1)
        self.assertEqual(
            models.NonDataAffiliateComponentAgreement.ERROR_TYPE_DOES_NOT_MATCH,
            e.exception.error_dict["signed_agreement"][0].messages[0],
        )

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.NonDataAffiliateComponentAgreementFactory.create()
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), str(instance.signed_agreement))

    def test_error_duplicate_signed_agreement(self):
        """Cannot link two member agreements to one signed_agreement."""
        instance_1 = factories.NonDataAffiliateComponentAgreementFactory.create()
        primary = factories.NonDataAffiliateAgreementFactory.create()
        instance_2 = factories.NonDataAffiliateComponentAgreementFactory.build(
            signed_agreement=instance_1.signed_agreement, component_of=primary
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

    def test_component_of_protect(self):
        """A NonDataAffiliateComponentAgreement is deleted if its component_of is deleted."""
        data_affiliate_agreement = factories.NonDataAffiliateAgreementFactory.create()
        component = factories.NonDataAffiliateComponentAgreementFactory.create(
            component_of=data_affiliate_agreement
        )
        data_affiliate_agreement.delete()
        with self.assertRaises(models.NonDataAffiliateComponentAgreement.DoesNotExist):
            component.refresh_from_db()
