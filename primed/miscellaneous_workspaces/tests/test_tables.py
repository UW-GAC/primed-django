"""Tests for the tables in the `miscellaneous_workspaces` app."""

from anvil_consortium_manager.models import Workspace
from django.test import TestCase

from .. import tables
from . import factories


class OpenAccessWorkspaceStaffTableTest(TestCase):
    """Tests for the OpenAccessWorkspaceStaffTable table."""

    model_factory = factories.OpenAccessWorkspaceFactory
    table_class = tables.OpenAccessWorkspaceStaffTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(Workspace.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(Workspace.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_two_objects(self):
        self.model_factory.create_batch(2)
        table = self.table_class(Workspace.objects.all())
        self.assertEqual(len(table.rows), 2)


class OpenAccessWorkspaceUserTableTest(TestCase):
    """Tests for the OpenAccessWorkspaceStaffTable table."""

    model_factory = factories.OpenAccessWorkspaceFactory
    table_class = tables.OpenAccessWorkspaceUserTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(Workspace.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(Workspace.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_two_objects(self):
        self.model_factory.create_batch(2)
        table = self.table_class(Workspace.objects.all())
        self.assertEqual(len(table.rows), 2)


class DataPrepWorkspaceUserTableTest(TestCase):
    """Tests for the DataPrepWorkspaceUserTable table."""

    model_factory = factories.DataPrepWorkspaceFactory
    table_class = tables.DataPrepWorkspaceUserTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(Workspace.objects.filter(workspace_type="data_prep"))
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(Workspace.objects.filter(workspace_type="data_prep"))
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_two_objects(self):
        self.model_factory.create_batch(2)
        table = self.table_class(Workspace.objects.filter(workspace_type="data_prep"))
        self.assertEqual(len(table.rows), 2)


class DataPrepWorkspaceStaffTableTest(TestCase):
    """Tests for the DataPrepWorkspaceUserTable table."""

    model_factory = factories.DataPrepWorkspaceFactory
    table_class = tables.DataPrepWorkspaceStaffTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(Workspace.objects.filter(workspace_type="data_prep"))
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(Workspace.objects.filter(workspace_type="data_prep"))
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_two_objects(self):
        self.model_factory.create_batch(2)
        table = self.table_class(Workspace.objects.filter(workspace_type="data_prep"))
        self.assertEqual(len(table.rows), 2)
