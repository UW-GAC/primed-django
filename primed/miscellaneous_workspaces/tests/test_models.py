""""Model tests for the `workspaces` app."""

from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.test import TestCase

from .. import models
from . import factories


class SimulatedDataWorkspaceTest(TestCase):
    """Tests for the SimulatedDataWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        instance = models.SimulatedDataWorkspace(workspace=workspace)
        instance.save()
        self.assertIsInstance(instance, models.SimulatedDataWorkspace)

    def test_str_method(self):
        workspace = WorkspaceFactory.create(
            billing_project__name="test-bp", name="test-ws"
        )
        instance = factories.SimulatedDataWorkspaceFactory.create(workspace=workspace)
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), "test-bp/test-ws")
