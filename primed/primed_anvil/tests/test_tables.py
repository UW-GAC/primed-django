from anvil_consortium_manager import models as acm_models
from anvil_consortium_manager.tests import factories as acm_factories
from django.test import TestCase

from .. import models, tables
from . import factories


class StudyTableTest(TestCase):
    model = models.Study
    model_factory = factories.StudyFactory
    table_class = tables.StudyTable

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


class dbGaPWorkspaceTableTest(TestCase):
    model = acm_models.Workspace
    model_factory = acm_factories.WorkspaceFactory
    table_class = tables.dbGaPWorkspaceTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create(workspace_type="dbgap")
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_two_objects(self):
        self.model_factory.create_batch(2, workspace_type="dbgap")
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 2)
