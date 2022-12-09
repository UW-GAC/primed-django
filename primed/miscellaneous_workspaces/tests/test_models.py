""""Model tests for the `workspaces` app."""

from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.core.exceptions import ValidationError
from django.test import TestCase

from primed.users.tests.factories import UserFactory

from .. import adapters, models
from . import factories


class SimulatedDataWorkspaceTest(TestCase):
    """Tests for the SimulatedDataWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        instance = models.SimulatedDataWorkspace(workspace=workspace, requested_by=user)
        instance.save()
        self.assertIsInstance(instance, models.SimulatedDataWorkspace)

    def test_str_method(self):
        workspace = WorkspaceFactory.create(
            billing_project__name="test-bp", name="test-ws"
        )
        instance = factories.SimulatedDataWorkspaceFactory.create(workspace=workspace)
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), "test-bp/test-ws")


class ConsortiumDevelWorkspaceTest(TestCase):
    """Tests for the ConsortiumDevelWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        instance = models.ConsortiumDevelWorkspace(
            workspace=workspace, requested_by=user
        )
        instance.save()
        self.assertIsInstance(instance, models.ConsortiumDevelWorkspace)

    def test_str_method(self):
        workspace = WorkspaceFactory.create(
            billing_project__name="test-bp", name="test-ws"
        )
        instance = factories.ConsortiumDevelWorkspaceFactory.create(workspace=workspace)
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), "test-bp/test-ws")


class ExampleWorkspaceTest(TestCase):
    """Tests for the ExampleWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        instance = models.ExampleWorkspace(workspace=workspace, requested_by=user)
        instance.save()
        self.assertIsInstance(instance, models.ExampleWorkspace)

    def test_str_method(self):
        workspace = WorkspaceFactory.create(
            billing_project__name="test-bp", name="test-ws"
        )
        instance = factories.ExampleWorkspaceFactory.create(workspace=workspace)
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), "test-bp/test-ws")


class TemplateWorkspaceTest(TestCase):
    """Tests for the TemplateWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        instance = models.TemplateWorkspace(workspace=workspace)
        instance.save()
        self.assertIsInstance(instance, models.TemplateWorkspace)

    def test_str_method(self):
        workspace = WorkspaceFactory.create(
            billing_project__name="test-bp", name="test-ws"
        )
        instance = factories.TemplateWorkspaceFactory.create(workspace=workspace)
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), "test-bp/test-ws")

    def test_clean_missing_intended_workspace_type_missing(self):
        workspace = WorkspaceFactory.create(
            billing_project__name="test-bp", name="test-ws"
        )
        instance = models.TemplateWorkspace(workspace=workspace)
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("intended_workspace_type", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["intended_workspace_type"]), 1)
        self.assertIn(
            "cannot be blank", e.exception.message_dict["intended_workspace_type"][0]
        )

    def test_clean_intended_workspace_type_blank(self):
        workspace = WorkspaceFactory.create(
            billing_project__name="test-bp", name="test-ws"
        )
        instance = factories.TemplateWorkspaceFactory.build(
            workspace=workspace,
            intended_workspace_type="",
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("intended_workspace_type", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["intended_workspace_type"]), 1)
        self.assertIn(
            "cannot be blank", e.exception.message_dict["intended_workspace_type"][0]
        )

    def test_clean_intended_workspace_type_with_registered_adapter(self):
        """No ValidationError is raised if intended_workspace_type is a registered type."""
        workspace = WorkspaceFactory.create(
            billing_project__name="test-bp", name="test-ws"
        )
        instance = factories.TemplateWorkspaceFactory.build(workspace=workspace)
        instance.full_clean()

    def test_clean_intended_workspace_type_with_unregistered_adapter(self):
        """ValidationError is raised if intended_workspace_type is not a registered type."""
        workspace = WorkspaceFactory.create(
            billing_project__name="test-bp", name="test-ws"
        )
        instance = factories.TemplateWorkspaceFactory.build(
            workspace=workspace, intended_workspace_type="foo"
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("intended_workspace_type", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["intended_workspace_type"]), 1)
        self.assertIn(
            "registered types", e.exception.message_dict["intended_workspace_type"][0]
        )

    def test_clean_intended_workspace_type_template(self):
        """ValidationError is raised if intended_workspace_type is set to "template"."""
        workspace = WorkspaceFactory.create(
            billing_project__name="test-bp", name="test-ws"
        )
        template_workspace_type = adapters.TemplateWorkspaceAdapter().get_type()
        instance = factories.TemplateWorkspaceFactory.build(
            workspace=workspace, intended_workspace_type=template_workspace_type
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("intended_workspace_type", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["intended_workspace_type"]), 1)
        self.assertIn(
            template_workspace_type,
            e.exception.message_dict["intended_workspace_type"][0],
        )
