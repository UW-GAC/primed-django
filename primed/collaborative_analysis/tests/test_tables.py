"""Tests for the tables in the `collaborative_analysis` app."""

from anvil_consortium_manager.models import Workspace
from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.test import TestCase

from .. import tables
from . import factories


class CollaborativeAnalysisWorkspaceStaffTableTest(TestCase):
    model = Workspace
    model_factory = factories.CollaborativeAnalysisWorkspaceFactory
    table_class = tables.CollaborativeAnalysisWorkspaceStaffTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_two_objects(self):
        self.model_factory.create_batch(2)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 2)

    def test_number_source_workspaces_zero(self):
        """Table shows correct count for number of source_workspaces."""
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_source_workspaces"), 0)

    def test_number_source_workspaces_one(self):
        """Table shows correct count for number of source_workspaces."""
        source_workspace = WorkspaceFactory.create()
        obj = self.model_factory.create()
        obj.source_workspaces.add(source_workspace)
        table = self.table_class(self.model.objects.filter(workspace_type="collab_analysis"))
        self.assertEqual(table.rows[0].get_cell("number_source_workspaces"), 1)

    def test_number_source_workspaces_two(self):
        """Table shows correct count for number of source_workspaces."""
        source_workspace_1 = WorkspaceFactory.create()
        source_workspace_2 = WorkspaceFactory.create()
        obj = self.model_factory.create()
        obj.source_workspaces.add(source_workspace_1)
        obj.source_workspaces.add(source_workspace_2)
        table = self.table_class(self.model.objects.filter(workspace_type="collab_analysis"))
        self.assertEqual(table.rows[0].get_cell("number_source_workspaces"), 2)


class CollaborativeAnalysisWorkspaceUserTableTest(TestCase):
    model = Workspace
    model_factory = factories.CollaborativeAnalysisWorkspaceFactory
    table_class = tables.CollaborativeAnalysisWorkspaceUserTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_two_objects(self):
        self.model_factory.create_batch(2)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 2)

    def test_number_source_workspaces_zero(self):
        """Table shows correct count for number of source_workspaces."""
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_source_workspaces"), 0)

    def test_number_source_workspaces_one(self):
        """Table shows correct count for number of source_workspaces."""
        source_workspace = WorkspaceFactory.create()
        obj = self.model_factory.create()
        obj.source_workspaces.add(source_workspace)
        table = self.table_class(self.model.objects.filter(workspace_type="collab_analysis"))
        self.assertEqual(table.rows[0].get_cell("number_source_workspaces"), 1)

    def test_number_source_workspaces_two(self):
        """Table shows correct count for number of source_workspaces."""
        source_workspace_1 = WorkspaceFactory.create()
        source_workspace_2 = WorkspaceFactory.create()
        obj = self.model_factory.create()
        obj.source_workspaces.add(source_workspace_1)
        obj.source_workspaces.add(source_workspace_2)
        table = self.table_class(self.model.objects.filter(workspace_type="collab_analysis"))
        self.assertEqual(table.rows[0].get_cell("number_source_workspaces"), 2)
