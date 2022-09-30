"""Tests for the tables in the `dbgap` app."""

from anvil_consortium_manager import models as acm_models
from django.test import TestCase

from .. import models, tables
from . import factories


class dbGaPStudyTableTest(TestCase):
    model = models.dbGaPStudy
    model_factory = factories.dbGaPStudyFactory
    table_class = tables.dbGaPStudyTable

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

    def test_number_workspaces(self):
        """Table shows correct count for number of workspaces."""
        self.model_factory.create()
        dbgap_study_2 = self.model_factory.create()
        factories.dbGaPWorkspaceFactory.create(dbgap_study=dbgap_study_2)
        dbgap_study_3 = self.model_factory.create()
        factories.dbGaPWorkspaceFactory.create_batch(2, dbgap_study=dbgap_study_3)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_workspaces"), 0)
        self.assertEqual(table.rows[1].get_cell("number_workspaces"), 1)
        self.assertEqual(table.rows[2].get_cell("number_workspaces"), 2)


class dbGaPWorkspaceTableTest(TestCase):
    model = acm_models.Workspace
    model_factory = factories.dbGaPWorkspaceFactory
    table_class = tables.dbGaPWorkspaceTable

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
