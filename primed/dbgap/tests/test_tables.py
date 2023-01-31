"""Tests for the tables in the `dbgap` app."""

from datetime import timedelta

from anvil_consortium_manager import models as acm_models
from anvil_consortium_manager.tests.factories import (
    WorkspaceAuthorizationDomainFactory,
    WorkspaceGroupSharingFactory,
)
from django.db.models import Count
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

    def test_principal_investigator(self):
        """The principal investigator field appears correctly with the correct link to the user detail page."""
        app = self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        name = app.principal_investigator.name
        url = app.principal_investigator.get_absolute_url()
        self.assertIn(name, table.rows[0].get_cell("principal_investigator"))
        self.assertIn(url, table.rows[0].get_cell("principal_investigator"))

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

    def test_number_requested_dars_zero(self):
        """Table shows correct count for number of requested DARs when an application has a snapshot but no DARs."""
        dbgap_application = self.model_factory.create()
        factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("number_requested_dars"), 0)

    def test_number_requested_dars_zero_no_snapshot(self):
        """Table shows correct count for number of requested DARs when no snapshots have been added."""
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertIsNone(table.rows[0].get_cell_value("number_requested_dars"))

    def test_number_requested_dars(self):
        """Table shows correct count for number of requested DARs when there is one."""
        dbgap_application = self.model_factory.create()
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.EXPIRED,
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.NEW,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("number_requested_dars"), 5)

    def test_number_requested_dars_two_applications(self):
        """Number of requested DARs is correct for two applications."""
        dbgap_application_1 = self.model_factory.create()
        dbgap_snapshot_1 = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application_1
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=dbgap_snapshot_1,
        )
        dbgap_application_2 = self.model_factory.create()
        dbgap_snapshot_2 = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application_2
        )
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=dbgap_snapshot_2,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("number_requested_dars"), 2)
        self.assertEqual(table.rows[1].get_cell_value("number_requested_dars"), 1)

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


class dbGaPDataAccessSnapshotTableTest(TestCase):
    model = models.dbGaPDataAccessSnapshot
    model_factory = factories.dbGaPDataAccessSnapshotFactory
    table_class = tables.dbGaPDataAccessSnapshotTable

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

    def test_number_approved_dars(self):
        snapshot = self.model_factory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.EXPIRED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.NEW,
        )
        other_snapshot = self.model_factory.create()
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=other_snapshot,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("number_approved_dars"), 1)
        self.assertEqual(table.rows[1].get_cell_value("number_approved_dars"), 2)


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

    def test_matching_workspace(self):
        """Table works if there is a matching workspace without access."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        WorkspaceAuthorizationDomainFactory.create(workspace=workspace.workspace)
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=workspace.dbgap_version,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertIn(
            "square-fill", table.rows[0].get_cell_value("in_authorization_domain")
        )

    def test_matching_workspace_with_access(self):
        """Table works if there is a matching workspace with access."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=workspace.dbgap_version,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        WorkspaceGroupSharingFactory.create(
            workspace=workspace.workspace,
            group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("workspace"), workspace)
        self.assertIn(
            "circle-fill", table.rows[0].get_cell_value("in_authorization_domain")
        )


class dbGaPDataAccessRequestSummaryTable(TestCase):

    model = models.dbGaPDataAccessRequest
    model_factory = factories.dbGaPDataAccessRequestFactory
    table_class = tables.dbGaPDataAccessRequestSummaryTable

    def annotate(self, qs):
        return qs.values("dbgap_dac", "dbgap_current_status").annotate(
            total=Count("pk")
        )

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.annotate(self.model.objects.all()))
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_row(self):
        self.model_factory.create()
        table = self.table_class(self.annotate(self.model.objects.all()))
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_two_dacs(self):
        self.model_factory.create(
            dbgap_dac="FOO", dbgap_current_status=self.model.APPROVED
        )
        self.model_factory.create(dbgap_dac="BAR", dbgap_current_status=self.model.NEW)
        table = self.table_class(self.annotate(self.model.objects.all()))
        self.assertEqual(len(table.rows), 2)
