"""Tests of models in the `primed_anvil` app."""

from anvil_consortium_manager.tests.factories import ManagedGroupFactory
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
        instance2 = factories.StudyFactory.build(short_name="FOO", full_name="full name")
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("short_name", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["short_name"]), 1)
        self.assertIn("already exists", e.exception.error_dict["short_name"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance2.save()


class StudySiteTest(TestCase):
    """Tests for the StudySite model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        instance = models.StudySite(full_name="Test name", short_name="TEST")
        instance.full_clean()
        instance.save()
        self.assertIsInstance(instance, models.StudySite)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.StudySiteFactory.create(short_name="Test")
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "Test")

    def test_get_absolute_url(self):
        """The get_absolute_url() method works."""
        instance = factories.StudySiteFactory()
        self.assertIsInstance(instance.get_absolute_url(), str)

    def test_unique_short_name(self):
        """Saving a model with a duplicate short name fails."""
        factories.StudySiteFactory.create(short_name="FOO")
        instance2 = models.StudySite(short_name="FOO", full_name="full name")
        with self.assertRaises(ValidationError):
            instance2.full_clean()
        with self.assertRaises(IntegrityError):
            instance2.save()

    def test_can_set_members_group(self):
        member_group = ManagedGroupFactory.create()
        instance = models.StudySite(full_name="Test name", short_name="TEST", member_group=member_group)
        instance.full_clean()
        instance.save()
        self.assertIsInstance(instance, models.StudySite)

    def test_same_member_group_different_sites(self):
        member_group = ManagedGroupFactory.create()
        factories.StudySiteFactory.create(member_group=member_group)
        instance = factories.StudySiteFactory.build(member_group=member_group)
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("member_group", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["member_group"]), 1)
        self.assertIn("Study site with this Member group already exists.", e.exception.message_dict["member_group"][0])


class AvailableDataTest(TestCase):
    """Tests for the AvailableData model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        instance = models.AvailableData(name="Test name", description="A description")
        instance.save()
        self.assertIsInstance(instance, models.AvailableData)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.AvailableDataFactory.create(name="Test name")
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "Test name")

    # def test_get_absolute_url(self):
    #     """The get_absolute_url() method works."""
    #     instance = factories.AvailableDataFactory()
    #     self.assertIsInstance(instance.get_absolute_url(), str)

    def test_unique_name(self):
        """Saving a model with a duplicate name fails."""
        factories.AvailableDataFactory.create(name="FOO")
        instance2 = factories.AvailableDataFactory.build(name="FOO")
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("name", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["name"]), 1)
        self.assertIn("already exists", e.exception.error_dict["name"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance2.save()
