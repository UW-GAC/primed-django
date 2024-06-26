"""Tests of models in the `duo` app."""

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase

from primed.dbgap.tests.factories import dbGaPWorkspaceFactory

from .. import models
from . import factories


class DataUsePermissionTest(TestCase):
    """Tests for the DataUsePermission model."""

    def test_model_saving(self):
        """Creation using model constructor and `.save()` works."""

        instance = models.DataUsePermission(
            term="test group",
            abbreviation="TEST",
            identifier="DUO:0000001",
            definition="The definition of this group",
        )
        instance.save()
        self.assertIsInstance(instance, models.DataUsePermission)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.DataUsePermissionFactory.create(term="test group", identifier="foo")
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "test group")

    def test_get_absolute_url(self):
        """The get_absolute_url method works."""
        instance = factories.DataUsePermissionFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)

    def test_get_ols_url(self):
        """The get_absolute_url method works."""
        instance = factories.DataUsePermissionFactory.create()
        self.assertIsInstance(instance.get_ols_url(), str)

    def test_can_add_child_node(self):
        root = factories.DataUsePermissionFactory.create()
        child = factories.DataUsePermissionFactory.create(parent=root)
        self.assertIn(child, root.children.all())

    def test_defaults(self):
        """Test defaults set by the model."""
        instance = models.DataUsePermission(
            identifier="DUO:0000001",
            abbreviation="TEST",
            term="test group",
            definition="foo",
        )
        instance.save()
        self.assertFalse(instance.requires_disease_term)
        self.assertFalse(instance.comment)

    def test_requires_disease_term(self):
        """Can set requires_disease_term to True."""
        instance = factories.DataUsePermissionFactory.create(
            requires_disease_term=True,
        )
        self.assertEqual(instance.requires_disease_term, True)

    def test_comment(self):
        """Can set requires_disease_term to True."""
        instance = factories.DataUsePermissionFactory.create(comment="test comment")
        self.assertEqual(instance.comment, "test comment")

    def test_unique_identifier(self):
        """Saving a model with a duplicate identifier fails."""
        factories.DataUsePermissionFactory.create(identifier="DUO:0000001")
        instance2 = factories.DataUsePermissionFactory.build(identifier="DUO:0000001")
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("identifier", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["identifier"]), 1)
        self.assertIn("already exists", e.exception.error_dict["identifier"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance2.save()

    def test_get_short_definition(self):
        instance = factories.DataUsePermissionFactory.create(definition="Test definition")
        self.assertEqual(instance.get_short_definition(), "Test definition")

    def test_get_short_definition_re_sub(self):
        instance = factories.DataUsePermissionFactory.create(definition="This XXX indicates that everything is fine.")
        self.assertEqual(instance.get_short_definition(), "Everything is fine.")

    def test_get_short_definition_capitalization(self):
        instance = factories.DataUsePermissionFactory.create(definition="Test definition XyXy")
        self.assertEqual(instance.get_short_definition(), "Test definition XyXy")


class DataUseModifierTest(TestCase):
    """Tests for the DataUseModifier model."""

    def test_model_saving(self):
        """Creation using model constructor and `.save()` works."""

        instance = models.DataUseModifier(
            term="test group",
            abbreviation="TEST",
            identifier="DUO:0000001",
            definition="The definition of this group",
        )
        instance.save()
        self.assertIsInstance(instance, models.DataUseModifier)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.DataUseModifierFactory.create(term="test group", identifier="foo")
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "test group")

    def test_get_absolute_url(self):
        """The get_absolute_url method works."""
        instance = factories.DataUseModifierFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)

    def test_get_ols_url(self):
        """The get_absolute_url method works."""
        instance = factories.DataUseModifierFactory.create()
        self.assertIsInstance(instance.get_ols_url(), str)

    def test_can_add_child_node(self):
        root = factories.DataUseModifierFactory.create()
        child = factories.DataUseModifierFactory.create(parent=root)
        self.assertIn(child, root.children.all())

    def test_defaults(self):
        """Test defaults set by the model."""
        instance = models.DataUseModifier(
            identifier="DUO:0000001",
            abbreviation="TEST",
            term="test group",
            definition="foo",
        )
        instance.save()
        self.assertFalse(instance.comment)

    def test_comment(self):
        """Can set requires_disease_term to True."""
        instance = factories.DataUseModifierFactory.create(comment="test comment")
        self.assertEqual(instance.comment, "test comment")

    def test_unique_identifier(self):
        """Saving a model with a duplicate identifier fails."""
        factories.DataUseModifierFactory.create(identifier="DUO:0000001")
        instance2 = factories.DataUseModifierFactory.build(identifier="DUO:0000001")
        with self.assertRaises(ValidationError) as e:
            instance2.full_clean()
        self.assertIn("identifier", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["identifier"]), 1)
        self.assertIn("already exists", e.exception.error_dict["identifier"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance2.save()

    def test_get_short_definition(self):
        instance = factories.DataUseModifierFactory.create(definition="Test definition")
        self.assertEqual(instance.get_short_definition(), "Test definition")

    def test_get_short_definition_re_sub(self):
        instance = factories.DataUseModifierFactory.create(definition="This XXX indicates that use is allowed.")
        self.assertEqual(instance.get_short_definition(), "Use is allowed.")


class DataUseOntologyTestCase(TestCase):
    """Tests for the DataUseOntology abstract model."""

    # Use the dbGaPWorkspace model to test this -- not ideal because it's defined in a different app but...

    def test_clean_requires_disease_term_false_with_no_disease_term(self):
        """Clean succeeds if disease_term is not set and requires_disease_term is False."""
        data_use_permission = factories.DataUsePermissionFactory.create(requires_disease_term=False)
        workspace = dbGaPWorkspaceFactory.create(data_use_permission=data_use_permission)
        # No errors should be raised.
        workspace.clean()

    def test_clean_requires_disease_term_true_with_disease_term(self):
        """Clean succeeds if disease_term is set and requires_disease_term is True."""
        data_use_permission = factories.DataUsePermissionFactory.create(requires_disease_term=True)
        workspace = dbGaPWorkspaceFactory.create(data_use_permission=data_use_permission, disease_term="foo")
        workspace.clean()

    def test_clean_requires_disease_term_false_with_disease_term(self):
        """Clean fails if disease_term is set when requires_disease_term is False."""
        data_use_permission = factories.DataUsePermissionFactory.create(requires_disease_term=False)
        workspace = dbGaPWorkspaceFactory.create(data_use_permission=data_use_permission, disease_term="foo")
        with self.assertRaises(ValidationError) as e:
            workspace.clean()
        self.assertIn("does not require a disease restriction", str(e.exception))

    def test_clean_requires_disease_term_true_with_no_disease_term(self):
        """Clean fails if disease_term is not set when requires_disease_term is True."""
        data_use_permission = factories.DataUsePermissionFactory.create(requires_disease_term=True)
        workspace = dbGaPWorkspaceFactory.create(
            data_use_permission=data_use_permission,
        )
        with self.assertRaises(ValidationError) as e:
            workspace.clean()
        self.assertIn("requires a disease restriction", str(e.exception))
