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

    def test_unique_short_name(self):
        """Saving a model with a duplicate short name fails."""
        factories.StudyFactory.create(short_name="FOO")
        instance2 = factories.StudyFactory.build(
            short_name="FOO", full_name="full name"
        )
        with self.assertRaises(ValidationError):
            instance2.full_clean()
        with self.assertRaises(IntegrityError):
            instance2.save()


class SiteTest(TestCase):
    """Tests for the Site model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        instance = models.Site(full_name="Test name", short_name="TEST")
        instance.save()
        self.assertIsInstance(instance, models.Site)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.SiteFactory.create(short_name="Test")
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "Test")

    def test_unique_short_name(self):
        """Saving a model with a duplicate short name fails."""
        factories.SiteFactory.create(short_name="FOO")
        instance2 = factories.SiteFactory.build(short_name="FOO", full_name="full name")
        with self.assertRaises(ValidationError):
            instance2.full_clean()
        with self.assertRaises(IntegrityError):
            instance2.save()
