"""Tests of models in the `duo` app."""

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase

from .. import models
from . import factories

# from primed.dbgap.tests.factories import dbGaPWorkspaceFactory


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
        instance = factories.DataUsePermissionFactory.create(
            term="test group", identifier="foo"
        )
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "test group (foo)")

    def test_can_add_child_node(self):
        root = factories.DataUsePermissionFactory.create()
        child = factories.DataUsePermissionFactory.create(parent=root)
        self.assertIn(child, root.get_children())

    def test_defaults(self):
        """Test defaults set by the model."""
        instance = models.DataUsePermission(
            identifier="DUO:0000001",
            abbreviation="TEST",
            term="test group",
            definition="foo",
        )
        instance.save()
        self.assertFalse(instance.requires_disease_restriction)
        self.assertFalse(instance.comment)

    def test_requires_disease_restriction(self):
        """Can set requires_disease_restriction to True."""
        instance = factories.DataUsePermissionFactory.create(
            requires_disease_restriction=True,
        )
        self.assertEqual(instance.requires_disease_restriction, True)

    def test_comment(self):
        """Can set requires_disease_restriction to True."""
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
        self.assertIn(
            "already exists", e.exception.error_dict["identifier"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance2.save()


# class DataUseModifierTest(TestCase):
#     """Tests for the DataUseModifier model."""
#
#     def test_model_saving(self):
#         """Creation using the model constructor and .save() works."""
#         instance = models.DataUseModifier(
#             code="GRU", description="General research use"
#         )
#         instance.save()
#         self.assertIsInstance(instance, models.DataUseModifier)
#
#     def test_str_method(self):
#         """The custom __str__ method returns the correct string."""
#         instance = factories.DataUseModifierFactory.create(code="TEST")
#         instance.save()
#         self.assertIsInstance(instance.__str__(), str)
#         self.assertEqual(instance.__str__(), "TEST")
#
#     def test_unique_code(self):
#         """Saving a model with a duplicate code fails."""
#         factories.DataUseModifierFactory.create(
#             code="TEST", description="test permission", identifier="DUO:0000001"
#         )
#         instance2 = factories.DataUseModifierFactory.build(
#             code="TEST", description="test permission 2", identifier="DUO:0000002"
#         )
#         with self.assertRaises(ValidationError) as e:
#             instance2.full_clean()
#         self.assertIn("code", e.exception.error_dict)
#         self.assertEqual(len(e.exception.error_dict["code"]), 1)
#         self.assertIn("already exists", e.exception.error_dict["code"][0].messages[0])
#         with self.assertRaises(IntegrityError):
#             instance2.save()
#
#     def test_unique_description(self):
#         """Saving a model with a duplicate description fails."""
#         factories.DataUseModifierFactory.create(
#             code="TEST1", description="test permission", identifier="DUO:0000001"
#         )
#         instance2 = factories.DataUseModifierFactory.build(
#             code="TEST2", description="test permission", identifier="DUO:0000002"
#         )
#         with self.assertRaises(ValidationError) as e:
#             instance2.full_clean()
#         self.assertIn("description", e.exception.error_dict)
#         self.assertEqual(len(e.exception.error_dict["description"]), 1)
#         self.assertIn(
#             "already exists", e.exception.error_dict["description"][0].messages[0]
#         )
#         with self.assertRaises(IntegrityError):
#             instance2.save()
#
#     def test_unique_identifier(self):
#         """Saving a model with a duplicate identifier fails."""
#         factories.DataUseModifierFactory.create(
#             code="TEST1", description="test permission 1", identifier="DUO:0000001"
#         )
#         instance2 = factories.DataUseModifierFactory.build(
#             code="TEST2", description="test permission 2", identifier="DUO:0000001"
#         )
#         with self.assertRaises(ValidationError) as e:
#             instance2.full_clean()
#         self.assertIn("identifier", e.exception.error_dict)
#         self.assertEqual(len(e.exception.error_dict["identifier"]), 1)
#         self.assertIn(
#             "already exists", e.exception.error_dict["identifier"][0].messages[0]
#         )
#         with self.assertRaises(IntegrityError):
#             instance2.save()


# class DataUseOntologyTestCase(TestCase):
#     """Tests for the DataUseOntology abstract model."""
#
#     # Use the dbGaPWorkspace model to test this -- not ideal because it's defined in a different app but...
#
#     def test_clean_requires_disease_restriction_false_with_no_disease_restriction(self):
#         """Clean succeeds if disease_restriction is not set and requires_disease_restriction is False."""
#         data_use_permission = factories.DataUsePermissionFactory.create(
#             requires_disease_restriction=False
#         )
#         workspace = dbGaPWorkspaceFactory.create(
#             data_use_permission=data_use_permission
#         )
#         # No errors should be raised.
#         workspace.clean()
#
#     def test_clean_requires_disease_restriction_true_with_disease_restriction(self):
#         """Clean succeeds if disease_restriction is set and requires_disease_restriction is True."""
#         data_use_permission = factories.DataUsePermissionFactory.create(
#             requires_disease_restriction=True
#         )
#         workspace = dbGaPWorkspaceFactory.create(
#             data_use_permission=data_use_permission, disease_restriction="foo"
#         )
#         workspace.clean()
#
#     def test_clean_requires_disease_restriction_false_with_disease_restriction(self):
#         """Clean fails if disease_restriction is set when requires_disease_restriction is False."""
#         data_use_permission = factories.DataUsePermissionFactory.create(
#             requires_disease_restriction=False
#         )
#         workspace = dbGaPWorkspaceFactory.create(
#             data_use_permission=data_use_permission, disease_restriction="foo"
#         )
#         with self.assertRaises(ValidationError) as e:
#             workspace.clean()
#         self.assertIn("does not require a disease restriction", str(e.exception))
#
#     def test_clean_requires_disease_restriction_true_with_no_disease_restriction(self):
#         """Clean fails if disease_restriction is not set when requires_disease_restriction is True."""
#         data_use_permission = factories.DataUsePermissionFactory.create(
#             requires_disease_restriction=True
#         )
#         workspace = dbGaPWorkspaceFactory.create(
#             data_use_permission=data_use_permission,
#         )
#         with self.assertRaises(ValidationError) as e:
#             workspace.clean()
#         self.assertIn("requires a disease restriction", str(e.exception))
