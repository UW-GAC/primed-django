"""Tests of models in the `primed_anvil` app."""

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import TestCase

from .. import models
from . import factories


class SiteTest(TestCase):
    """Tests for the StudySite model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        instance = models.StudySite(full_name="Test name", short_name="TEST")
        instance.save()
        self.assertIsInstance(instance, models.StudySite)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.StudySiteFactory.create(short_name="Test")
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "Test")

    def test_unique_short_name(self):
        """Saving a model with a duplicate short name fails."""
        factories.StudySiteFactory.create(short_name="FOO")
        instance2 = factories.StudySiteFactory.build(
            short_name="FOO", full_name="full name"
        )
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("short_name", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["short_name"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["short_name"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance2.save()


class StudyTest(TestCase):
    """Tests for the Study model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        instance = models.Study(full_name="Test name", short_name="TEST")
        instance.save()
        self.assertIsInstance(instance, models.Study)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.StudyFactory.create(short_name="Test")
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "Test")

    def test_unique_short_name(self):
        """Saving a model with a duplicate short name fails."""
        factories.StudyFactory.create(short_name="FOO")
        instance2 = factories.StudyFactory.build(
            short_name="FOO", full_name="full name"
        )
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("short_name", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["short_name"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["short_name"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance2.save()


class DataUsePermissionTest(TestCase):
    """Tests for the DataUsePermission model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        instance = models.DataUsePermission(
            code="GRU", description="General research use", identifier="DUO:0000001"
        )
        instance.save()
        self.assertIsInstance(instance, models.DataUsePermission)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.DataUsePermissionFactory.create(code="TEST")
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "TEST")

    def test_unique_code(self):
        """Saving a model with a duplicate code fails."""
        factories.DataUseModifierFactory.create(
            code="TEST", description="test permission", identifier="DUO:0000001"
        )
        instance2 = factories.DataUseModifierFactory.build(
            code="TEST", description="test permission 2", identifier="DUO:0000002"
        )
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("code", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["code"]), 1)
        self.assertIn("already exists", e.exception.error_dict["code"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance2.save()

    def test_unique_description(self):
        """Saving a model with a duplicate description fails."""
        factories.DataUsePermissionFactory.create(
            code="TEST1", description="test permission", identifier="DUO:0000001"
        )
        instance2 = factories.DataUsePermissionFactory.build(
            code="TEST2", description="test permission", identifier="DUO:9999999"
        )
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("description", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["description"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["description"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance2.save()

    def test_unique_identifier(self):
        """Saving a model with a duplicate identifier fails."""
        factories.DataUsePermissionFactory.create(
            code="TEST1", description="test permission 1", identifier="DUO:0000001"
        )
        instance2 = factories.DataUsePermissionFactory.build(
            code="TEST2", description="test permission 2", identifier="DUO:0000001"
        )
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("identifier", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["identifier"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["identifier"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance2.save()


class DataUseModifierTest(TestCase):
    """Tests for the DataUseModifier model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        instance = models.DataUseModifier(
            code="GRU", description="General research use"
        )
        instance.save()
        self.assertIsInstance(instance, models.DataUseModifier)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.DataUseModifierFactory.create(code="TEST")
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "TEST")

    def test_unique_code(self):
        """Saving a model with a duplicate code fails."""
        factories.DataUseModifierFactory.create(
            code="TEST", description="test permission", identifier="DUO:0000001"
        )
        instance2 = factories.DataUseModifierFactory.build(
            code="TEST", description="test permission 2", identifier="DUO:0000002"
        )
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("code", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["code"]), 1)
        self.assertIn("already exists", e.exception.error_dict["code"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance2.save()

    def test_unique_description(self):
        """Saving a model with a duplicate description fails."""
        factories.DataUseModifierFactory.create(
            code="TEST1", description="test permission", identifier="DUO:0000001"
        )
        instance2 = factories.DataUseModifierFactory.build(
            code="TEST2", description="test permission", identifier="DUO:0000002"
        )
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("description", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["description"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["description"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance2.save()

    def test_unique_identifier(self):
        """Saving a model with a duplicate identifier fails."""
        factories.DataUseModifierFactory.create(
            code="TEST1", description="test permission 1", identifier="DUO:0000001"
        )
        instance2 = factories.DataUseModifierFactory.build(
            code="TEST2", description="test permission 2", identifier="DUO:0000001"
        )
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("identifier", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["identifier"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["identifier"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance2.save()


class StudyConsentGroupTest(TestCase):
    """Tests for the StudyConsentGroup model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        study = factories.StudyFactory.create()
        dup = factories.DataUsePermissionFactory.create()
        instance = models.StudyConsentGroup(
            study=study,
            data_use_permission=dup,
            full_consent_code="TEST",
            data_use_limitations="Data can only be used for test purposes.",
        )
        instance.save()
        self.assertIsInstance(instance, models.StudyConsentGroup)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.StudyConsentGroupFactory.create(
            study__short_name="Study", full_consent_code="Code"
        )
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "Study - Code")

    def test_unique_study_consent_group(self):
        """Saving a duplicate model fails."""
        study = factories.StudyFactory.create()
        dup_1 = factories.DataUsePermissionFactory.create()
        dup_2 = factories.DataUsePermissionFactory.create()
        full_consent_code = "TEST-NPU-COL"
        factories.StudyConsentGroupFactory.create(
            study=study, full_consent_code=full_consent_code, data_use_permission=dup_1
        )
        instance_2 = factories.StudyConsentGroupFactory.build(
            study=study, full_consent_code=full_consent_code, data_use_permission=dup_2
        )
        with self.assertRaises(ValidationError) as e:
            instance_2.full_clean()
        self.assertIn("__all__", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["__all__"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["__all__"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance_2.save()

    def test_study_protect(self):
        """Cannot delete a Study if it has an associated StudyConsentGroup."""
        study = factories.StudyFactory.create()
        factories.StudyConsentGroupFactory.create(study=study)
        with self.assertRaises(ProtectedError):
            study.delete()

    def test_data_use_permission_protect(self):
        """Cannot delete a DataUsePermission if it has an associated StudyConsentGroup."""
        dup = factories.DataUsePermissionFactory.create()
        factories.StudyConsentGroupFactory.create(data_use_permission=dup)
        with self.assertRaises(ProtectedError):
            dup.delete()
