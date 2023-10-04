"""Tests for the tables in the `dbgap` app."""

from datetime import timedelta

from anvil_consortium_manager import models as acm_models
from anvil_consortium_manager.tests.factories import GroupGroupMembershipFactory
from django.db.models import Count
from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

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

    def test_ordering(self):
        """Instances are ordered alphabetically by dbgap_phs."""
        instance_1 = self.model_factory.create(dbgap_phs=2)
        instance_2 = self.model_factory.create(dbgap_phs=1)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2)
        self.assertEqual(table.data[1], instance_1)


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

    def test_render_dbgap_accession(self):
        """render_dbgap_accession returns the correct value."""
        instance = self.model_factory.create(
            dbgap_study_accession__dbgap_phs=1,
            dbgap_version=2,
            dbgap_participant_set=3,
        )
        table = self.table_class(self.model.objects.all())
        self.assertIn(
            "phs000001.v2.p3",
            table.rows[0].get_cell_value("dbgap_accession"),
        )
        self.assertIn(
            instance.get_dbgap_link(), table.rows[0].get_cell_value("dbgap_accession")
        )

    def test_render_number_approved_dars_no_dars(self):
        instance = self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.render_number_approved_dars(instance.workspace), 0)

    def test_render_number_approved_dars_one_dar(self):
        instance = self.model_factory.create()
        factories.dbGaPDataAccessRequestForWorkspaceFactory(dbgap_workspace=instance)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.render_number_approved_dars(instance.workspace), 1)

    def test_render_number_approved_dars_one_dar_does_not_match(self):
        instance = self.model_factory.create()
        factories.dbGaPDataAccessRequestFactory()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.render_number_approved_dars(instance.workspace), 0)

    def test_render_number_approved_dars_two_dars(self):
        instance = self.model_factory.create()
        factories.dbGaPDataAccessRequestForWorkspaceFactory(dbgap_workspace=instance)
        factories.dbGaPDataAccessRequestForWorkspaceFactory(dbgap_workspace=instance)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.render_number_approved_dars(instance.workspace), 2)

    def test_render_number_approved_dars_not_approved(self):
        instance = self.model_factory.create()
        factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=instance,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.render_number_approved_dars(instance.workspace), 0)

    def test_render_number_approved_dars_only_most_recent(self):
        instance = self.model_factory.create()
        factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=instance, dbgap_data_access_snapshot__is_most_recent=False
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.render_number_approved_dars(instance.workspace), 0)

    # def test_render_is_shared_not_shared(self):
    #     """render_is_shared works correctly when the workspace is not shared with anyone."""
    #     factories.ManagedGroupFactory.create(name="PRIMED_ALL")
    #     factories.dbGaPWorkspaceFactory.create()
    #     table = self.table_class(self.model.objects.all())
    #     self.assertEqual("", table.rows[0].get_cell_value("is_shared"))

    # def test_render_is_shared_true(self):
    #     """render_is_shared works correctly when the workspace is shared with PRIMED_ALL."""
    #     group = factories.ManagedGroupFactory.create(name="PRIMED_ALL")
    #     dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
    #     WorkspaceGroupSharingFactory.create(
    #         group=group, workspace=dbgap_workspace.workspace
    #     )
    #     table = self.table_class(self.model.objects.all())
    #     import ipdb; ipdb.set_trace()
    #     self.assertIn("circle-fill", table.rows[0].get_cell_value("is_shared"))

    # def test_render_is_shared_shared_with_different_group(self):
    #     """render_is_shared works correctly when the workspace is shared with a group other PRIMED_ALL."""
    #     factories.ManagedGroupFactory.create(name="PRIMED_ALL")
    #     group = factories.ManagedGroupFactory.create()
    #     dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
    #     WorkspaceGroupSharingFactory.create(
    #         group=group, workspace=dbgap_workspace.workspace
    #     )
    #     table = self.table_class(self.model.objects.all())
    #     self.assertEqual("", table.rows[0].get_cell_value("is_shared"))


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
        self.assertEqual(table.rows[0].get_cell_value("number_approved_dars"), "0")

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
        self.assertEqual(table.rows[0].get_cell_value("number_approved_dars"), "1")

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
        self.assertEqual(table.rows[0].get_cell_value("number_approved_dars"), "2")

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
        self.assertEqual(table.rows[0].get_cell_value("number_approved_dars"), "1")

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
        self.assertEqual(table.rows[0].get_cell_value("number_approved_dars"), "2")
        self.assertEqual(table.rows[1].get_cell_value("number_approved_dars"), "1")

    def test_number_requested_dars_zero(self):
        """Table shows correct count for number of requested DARs when an application has a snapshot but no DARs."""
        dbgap_application = self.model_factory.create()
        factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell_value("number_requested_dars"), "0")

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
        self.assertEqual(table.rows[0].get_cell_value("number_requested_dars"), "5")

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
        self.assertEqual(table.rows[0].get_cell_value("number_requested_dars"), "2")
        self.assertEqual(table.rows[1].get_cell_value("number_requested_dars"), "1")

    def test_last_update_no_snapshot(self):
        """Last update is --- with no snapshot."""
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertIsNone(table.rows[0].get_cell_value("last_update"))

    def test_last_update_one_snapshot(self):
        """Last update shows correct date with one snapshot."""
        dbgap_application = self.model_factory.create()
        snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application
        )
        table = self.table_class(self.model.objects.all())
        self.assertIsNotNone(table.rows[0].get_cell_value("last_update"))
        self.assertIn(
            snapshot.get_absolute_url(), table.rows[0].get_cell("last_update")
        )

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
        self.assertIn(
            latest_snapshot.get_absolute_url(), table.rows[0].get_cell("last_update")
        )

    def test_ordering(self):
        """Instances are ordered alphabetically by dbgap_project_id."""
        instance_1 = self.model_factory.create(dbgap_project_id=2)
        instance_2 = self.model_factory.create(dbgap_project_id=1)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2)
        self.assertEqual(table.data[1], instance_1)


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
        snapshot_1 = self.model_factory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=snapshot_1,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot_1,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot_1,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot_1,
            dbgap_current_status=models.dbGaPDataAccessRequest.EXPIRED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot_1,
            dbgap_current_status=models.dbGaPDataAccessRequest.NEW,
        )
        snapshot_2 = self.model_factory.create()
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot_2,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.render_number_approved_dars(snapshot_1), 1)
        self.assertEqual(table.render_number_approved_dars(snapshot_2), 2)

    def test_number_requested_dars(self):
        snapshot_1 = self.model_factory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=snapshot_1,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot_1,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot_1,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot_1,
            dbgap_current_status=models.dbGaPDataAccessRequest.EXPIRED,
        )
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot_1,
            dbgap_current_status=models.dbGaPDataAccessRequest.NEW,
        )
        snapshot_2 = self.model_factory.create()
        factories.dbGaPDataAccessRequestFactory.create_batch(
            2,
            dbgap_data_access_snapshot=snapshot_2,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.render_number_requested_dars(snapshot_1), 9)
        self.assertEqual(table.render_number_requested_dars(snapshot_2), 2)

    def test_ordering(self):
        """Instances are ordered by decreasing snapshot date."""
        with freeze_time("2020-01-01"):
            instance_1 = self.model_factory.create()
        with freeze_time("2021-12-12"):
            instance_2 = self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2)
        self.assertEqual(table.data[1], instance_1)


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

    def test_render_dbgap_accession(self):
        instance = self.model_factory.create(
            dbgap_phs=1, original_version=2, original_participant_set=3
        )
        table = self.table_class(self.model.objects.all())
        self.assertIn("phs000001.v2.p3", table.render_dbgap_accession(instance))

    def test_ordering(self):
        """Instances are ordered alphabetically by dbgap_application and dbgap_dar_id."""
        dbgap_application_1 = factories.dbGaPApplicationFactory.create(
            dbgap_project_id=2
        )
        dbgap_application_2 = factories.dbGaPApplicationFactory.create(
            dbgap_project_id=1
        )
        instance_1 = self.model_factory.create(
            dbgap_dar_id=4,
            dbgap_data_access_snapshot__dbgap_application=dbgap_application_1,
        )
        instance_2 = self.model_factory.create(
            dbgap_dar_id=3,
            dbgap_data_access_snapshot__dbgap_application=dbgap_application_2,
        )
        instance_3 = self.model_factory.create(
            dbgap_dar_id=2,
            dbgap_data_access_snapshot__dbgap_application=dbgap_application_1,
        )
        instance_4 = self.model_factory.create(
            dbgap_dar_id=1,
            dbgap_data_access_snapshot__dbgap_application=dbgap_application_2,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_4)
        self.assertEqual(table.data[1], instance_2)
        self.assertEqual(table.data[2], instance_3)
        self.assertEqual(table.data[3], instance_1)


class dbGaPDataAccessRequestBySnapshotTableTest(TestCase):
    model = models.dbGaPDataAccessRequest
    model_factory = factories.dbGaPDataAccessRequestFactory
    table_class = tables.dbGaPDataAccessRequestBySnapshotTable

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

    def test_one_matching_workspace_with_access(self):
        """Table works if there is a matching workspace with access."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace
        )
        GroupGroupMembershipFactory.create(
            parent_group=workspace.workspace.authorization_domains.first(),
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_access_group,
        )
        table = self.table_class([dar])
        value = table.render_matching_workspaces(dar.get_dbgap_workspaces(), dar)
        self.assertIn(workspace.workspace.name, value)
        self.assertNotIn(workspace.workspace.billing_project.name, value)
        self.assertIn("circle-fill", value)

    def test_one_matching_workspace_without_access(self):
        """Table works if there is a matching workspace with access."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace
        )
        table = self.table_class([dar])
        value = table.render_matching_workspaces(dar.get_dbgap_workspaces(), dar)
        self.assertIn(workspace.workspace.name, value)
        self.assertIn("square-fill", value)

    def test_two_matching_workspaces(self):
        """Table works if there is are two matching workspaces."""
        study_accession = factories.dbGaPStudyAccessionFactory.create()
        workspace_1 = factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession=study_accession,
            dbgap_version=1,
            dbgap_participant_set=1,
            dbgap_consent_code=1,
        )
        workspace_2 = factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession=study_accession,
            dbgap_version=2,
            dbgap_participant_set=1,
            dbgap_consent_code=1,
        )
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=study_accession.dbgap_phs,
            original_version=1,
            original_participant_set=1,
            dbgap_consent_code=1,
        )
        table = self.table_class([dar])
        value = table.render_matching_workspaces(dar.get_dbgap_workspaces(), dar)
        self.assertIn(workspace_1.workspace.name, value)
        self.assertIn(workspace_2.workspace.name, value)

    def test_ordering(self):
        """Instances are ordered alphabetically by dbgap_dar_id."""
        instance_1 = self.model_factory.create(dbgap_dar_id=2)
        instance_2 = self.model_factory.create(dbgap_dar_id=1)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2)
        self.assertEqual(table.data[1], instance_1)


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
