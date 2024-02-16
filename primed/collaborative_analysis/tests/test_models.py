from anvil_consortium_manager.tests.factories import (
    ManagedGroupFactory,
    WorkspaceFactory,
)
from django.test import TestCase

from primed.users.tests.factories import UserFactory

from .. import models
from . import factories


class CollaborativeAnalysisWorkspaceTest(TestCase):
    """Tests for the DataPrepWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        group = ManagedGroupFactory.create()
        instance = models.CollaborativeAnalysisWorkspace(
            workspace=workspace,
            custodian=user,
            analyst_group=group,
        )
        instance.save()
        self.assertIsInstance(instance, models.CollaborativeAnalysisWorkspace)

    def test_str_method(self):
        instance = factories.CollaborativeAnalysisWorkspaceFactory.create()
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), str(instance.workspace))

    def test_one_source_workspace(self):
        source_workspace = WorkspaceFactory.create()
        instance = factories.CollaborativeAnalysisWorkspaceFactory.create()
        instance.source_workspaces.add(source_workspace)
        self.assertEqual(len(instance.source_workspaces.all()), 1)
        self.assertIn(source_workspace, instance.source_workspaces.all())

    def test_two_source_workspaces(self):
        source_workspace_1 = WorkspaceFactory.create()
        source_workspace_2 = WorkspaceFactory.create()
        instance = factories.CollaborativeAnalysisWorkspaceFactory.create()
        instance.source_workspaces.add(source_workspace_1, source_workspace_2)
        self.assertEqual(len(instance.source_workspaces.all()), 2)
        self.assertIn(source_workspace_1, instance.source_workspaces.all())
        self.assertIn(source_workspace_2, instance.source_workspaces.all())
