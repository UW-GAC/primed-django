"""Tests of models in the `primed_anvil` app."""

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase

from .. import models
from . import factories


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

    def test_get_absolute_url(self):
        """The get_absolute_url() method works."""
        instance = factories.StudyFactory()
        self.assertIsInstance(instance.get_absolute_url(), str)

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

    def test_defaults(self):
        """Test defaults set by the model."""
        instance = models.DataUsePermission(
            code="GRU", description="General research use", identifier="DUO:0000001"
        )
        instance.save()
        self.assertEqual(instance.requires_disease_restriction, False)

    def test_requires_disease_restriction(self):
        """Can set requires_disease_restriction to True."""
        instance = models.DataUsePermission(
            code="GRU",
            description="General research use",
            identifier="DUO:0000001",
            requires_disease_restriction=True,
        )
        instance.save()
        self.assertEqual(instance.requires_disease_restriction, True)

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
