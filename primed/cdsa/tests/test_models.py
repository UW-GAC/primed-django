"""Tests of models in the `cdsa` app."""

from anvil_consortium_manager.tests.factories import ManagedGroupFactory
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase

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
        #        study = StudyFactory.create()
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
