"""Tests for the tables in the `dbgap` app."""

from datetime import timedelta

from anvil_consortium_manager import models as acm_models
from django.test import TestCase
from django.utils import timezone

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
        """Table shows correct count for number of approved DARs when an application has a snapshot but no DARs."""
        dbgap_application = self.model_factory.create()
        factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("number_approved_dars"), 0)

    def test_number_approved_dars_zero_no_snapshot(self):
        """Table shows correct count for number of approved DARs when no snapshots have been added."""
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertIsNone(table.rows[0].get_cell_value("number_approved_dars"))

    def test_number_approved_dars_one(self):
        """Table shows correct count for number of approved DARs when there is one."""
        dbgap_application = self.model_factory.create()
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("number_approved_dars"), 1)

    def test_number_approved_dars_two(self):
        """Table shows correct count for number of approved DARs when there are two."""
        dbgap_application = self.model_factory.create()
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("number_approved_dars"), 2)

    def test_number_approved_dars_other(self):
        """Number of approved DARs does not include DARs with status that is not "approved"."""
        dbgap_application = self.model_factory.create()
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.EXPIRED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.NEW,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("number_approved_dars"), 1)

    def test_number_approved_dars_two_applications(self):
        """Number of approved DARs is correct for two applications."""
        dbgap_application_1 = self.model_factory.create()
        dbgap_snapshot_1 = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application_1
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=dbgap_snapshot_1,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        dbgap_application_2 = self.model_factory.create()
        dbgap_snapshot_2 = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application_2
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=dbgap_snapshot_2,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("number_approved_dars"), 2)
        self.assertEqual(table.rows[1].get_cell_value("number_approved_dars"), 1)

    def test_last_update_no_snapshot(self):
        """Last update is --- with no snapshot."""
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertIsNone(table.rows[0].get_cell_value("last_update"))

    def test_last_update_one_snapshot(self):
        """Last update shows correct date with one snapshot."""
        dbgap_application = self.model_factory.create()
        factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application
        )
        table = self.table_class(self.model.objects.all())
        self.assertIsNotNone(table.rows[0].get_cell_value("last_update"))

    def test_last_update_two_snapshots(self):
        """Last update shows correct date with two snapshots."""
        dbgap_application = self.model_factory.create()
        last_month = timezone.now() - timedelta(weeks=4)
        factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application, created=last_month
        )
        latest_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application, created=timezone.now()
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(
            table.rows[0].get_cell_value("last_update"), latest_snapshot.created
        )


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
