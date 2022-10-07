"""Tests for the tables in the `dbgap` app."""

from anvil_consortium_manager import models as acm_models
from django.test import TestCase

from .. import models, tables
from . import factories


class dbGaPStudyAccessionTableTest(TestCase):
    model = models.dbGaPStudyAccession
    model_factory = factories.dbGaPStudyAccessionFactory
    table_class = tables.dbGaPStudyAccessionTable

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
        dbgap_study_accession_2 = self.model_factory.create()
        factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession=dbgap_study_accession_2
        )
        dbgap_study_accession_3 = self.model_factory.create()
        factories.dbGaPWorkspaceFactory.create_batch(
            2, dbgap_study_accession=dbgap_study_accession_3
        )
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


class dbGaPApplicationTableTest(TestCase):
    model = models.dbGaPApplication
    model_factory = factories.dbGaPApplicationFactory
    table_class = tables.dbGaPApplicationTable

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

    def test_number_approved_dars_zero(self):
        """Table shows correct count for number of approved DARs when there is zero."""
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_approved_dars"), 0)

    def test_number_approved_dars_one(self):
        """Table shows correct count for number of approved DARs when there is one."""
        dbgap_application = self.model_factory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=dbgap_application,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_approved_dars"), 1)

    def test_number_approved_dars_two(self):
        """Table shows correct count for number of approved DARs when there are two."""
        dbgap_application = self.model_factory.create()
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_application=dbgap_application,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_approved_dars"), 2)

    def test_number_approved_dars_other(self):
        """Number of approved DARs does not include DARs with status that is not "approved"."""
        dbgap_application = self.model_factory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=dbgap_application,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=dbgap_application,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=dbgap_application,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=dbgap_application,
            dbgap_current_status=models.dbGaPDataAccessRequest.EXPIRED,
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=dbgap_application,
            dbgap_current_status=models.dbGaPDataAccessRequest.NEW,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_approved_dars"), 1)


class dbGaPDataAccessRequestTableTest(TestCase):
    model = models.dbGaPDataAccessRequest
    model_factory = factories.dbGaPDataAccessRequestFactory
    table_class = tables.dbGaPDataAccessRequestTable

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
