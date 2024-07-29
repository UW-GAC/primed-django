"""Tests of helper functions in the `primed_anvil` app."""

from anvil_consortium_manager.tests.factories import (
    ManagedGroupFactory,
    WorkspaceGroupSharingFactory,
)
from django.test import TestCase

from primed.cdsa.tests.factories import CDSAWorkspaceFactory
from primed.dbgap.tests.factories import (
    dbGaPStudyAccessionFactory,
    dbGaPWorkspaceFactory,
)
from primed.miscellaneous_workspaces.tests.factories import OpenAccessWorkspaceFactory
from primed.primed_anvil.tests.factories import AvailableDataFactory, StudyFactory

from .. import helpers


class GetSummaryTableDataTest(TestCase):
    """Tests for the helpers.get_summary_table_data method."""

    def test_no_workspaces_no_available_data_instnaces(self):
        """helpers.get_summary_table_data with no workspaces."""
        with self.assertRaises(RuntimeError):
            helpers.get_summary_table_data()

    def test_no_workspaces_one_available_data_instance(self):
        """helpers.get_summary_table_data with no workspaces."""
        AvailableDataFactory.create()
        res = helpers.get_summary_table_data()
        self.assertEqual(res, [])

    def test_one_dbgap_workspace_one_study_not_shared_no_available_data(self):
        AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study])
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 4)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "dbGaP")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], False)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], False)

    def test_one_open_access_workspace_one_study_not_shared_no_available_data(self):
        AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        workspace = OpenAccessWorkspaceFactory.create()
        workspace.studies.add(study)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 4)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "Open access")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], False)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], False)

    def test_one_dbgap_workspace_one_study_not_shared_with_one_available_data(self):
        available_data = AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        workspace = dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study])
        workspace.available_data.add(available_data)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 4)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "dbGaP")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], False)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], True)

    def test_one_dbgap_workspace_one_study_not_shared_with_two_available_data(self):
        available_data_1 = AvailableDataFactory.create(name="Foo")
        available_data_2 = AvailableDataFactory.create(name="Bar")
        study = StudyFactory.create(short_name="TEST")
        workspace = dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study])
        workspace.available_data.add(available_data_1)
        workspace.available_data.add(available_data_2)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 5)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "dbGaP")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], False)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], True)

    def test_one_dbgap_workspace_two_studies_not_shared_no_available_data(self):
        AvailableDataFactory.create(name="Foo")
        study_1 = StudyFactory.create(short_name="TEST")
        study_2 = StudyFactory.create(short_name="Other")
        dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study_1, study_2])
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 4)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "Other, TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "dbGaP")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], False)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], False)

    def test_one_dbgap_workspace_one_study_shared_no_available_data(self):
        AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        workspace = dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study])
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group__name="PRIMED_ALL")
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 4)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "dbGaP")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], True)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], False)

    def test_two_dbgap_workspaces_one_study(self):
        AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study])
        dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study])
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 4)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "dbGaP")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], False)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], False)

    def test_two_dbgap_workspaces_one_study_one_shared(self):
        available_data_1 = AvailableDataFactory.create(name="Foo")
        available_data_2 = AvailableDataFactory.create(name="Bar")
        study = StudyFactory.create(short_name="TEST")
        workspace_1 = dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study])
        workspace_1.available_data.add(available_data_1)
        WorkspaceGroupSharingFactory.create(workspace=workspace_1.workspace, group__name="PRIMED_ALL")
        workspace_2 = dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study])
        workspace_2.available_data.add(available_data_2)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 2)
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": True,
                "access_mechanism": "dbGaP",
                "Foo": True,
                "Bar": False,
            },
            res,
        )
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "dbGaP",
                "Foo": False,
                "Bar": True,
            },
            res,
        )

    def test_two_dbgap_workspaces_multiple_studies(self):
        AvailableDataFactory.create(name="Foo")
        study_1 = StudyFactory.create(short_name="TEST")
        study_2 = StudyFactory.create(short_name="Other")
        dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study_1, study_2])
        dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study_1])
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 2)
        self.assertIn(
            {
                "study": "Other, TEST",
                "is_shared": False,
                "access_mechanism": "dbGaP",
                "Foo": False,
            },
            res,
        )
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "dbGaP",
                "Foo": False,
            },
            res,
        )

    def test_one_dbgap_workspace_one_open_access_workspace_different_studies(self):
        AvailableDataFactory.create(name="Foo")
        study_1 = StudyFactory.create(short_name="TEST")
        dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study_1])
        study_2 = StudyFactory.create(short_name="Other")
        workspace = OpenAccessWorkspaceFactory.create()
        workspace.studies.add(study_2)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 2)
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "dbGaP",
                "Foo": False,
            },
            res,
        )
        self.assertIn(
            {
                "study": "Other",
                "is_shared": False,
                "access_mechanism": "Open access",
                "Foo": False,
            },
            res,
        )

    def test_one_dbgap_workspace_one_open_access_workspace_same_study(self):
        AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study])
        workspace = OpenAccessWorkspaceFactory.create()
        workspace.studies.add(study)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 2)
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "dbGaP",
                "Foo": False,
            },
            res,
        )
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "Open access",
                "Foo": False,
            },
            res,
        )

    def test_one_dbgap_workspace_one_open_access_workspace_different_available_data(
        self,
    ):
        available_data_1 = AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        workspace = dbGaPWorkspaceFactory.create(dbgap_study_accession__studies=[study])
        workspace.available_data.add(available_data_1)
        workspace = OpenAccessWorkspaceFactory.create()
        workspace.studies.add(study)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 2)
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "dbGaP",
                "Foo": True,
            },
            res,
        )
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "Open access",
                "Foo": False,
            },
            res,
        )

    def test_one_cdsa_workspace_not_shared_no_available_data(self):
        AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        CDSAWorkspaceFactory.create(study=study)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 4)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "CDSA")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], False)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], False)

    def test_one_cdsa_workspace_not_shared_with_one_available_data(self):
        available_data = AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        workspace = CDSAWorkspaceFactory.create(study=study)
        workspace.available_data.add(available_data)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 4)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "CDSA")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], False)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], True)

    def test_one_cdsa_workspace_not_shared_with_two_available_data(self):
        available_data_1 = AvailableDataFactory.create(name="Foo")
        available_data_2 = AvailableDataFactory.create(name="Bar")
        study = StudyFactory.create(short_name="TEST")
        workspace = CDSAWorkspaceFactory.create(
            study=study,
        )
        workspace.available_data.add(available_data_1)
        workspace.available_data.add(available_data_2)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 5)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "CDSA")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], False)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], True)

    def test_one_cdsa_workspace_one_study_shared_no_available_data(self):
        AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        workspace = CDSAWorkspaceFactory.create(study=study)
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group__name="PRIMED_ALL")
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 4)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "CDSA")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], True)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], False)

    def test_two_cdsa_workspaces_one_study(self):
        AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        CDSAWorkspaceFactory.create(study=study)
        CDSAWorkspaceFactory.create(study=study)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]), 4)
        self.assertIn("study", res[0])
        self.assertEqual(res[0]["study"], "TEST")
        self.assertIn("access_mechanism", res[0])
        self.assertEqual(res[0]["access_mechanism"], "CDSA")
        self.assertIn("is_shared", res[0])
        self.assertEqual(res[0]["is_shared"], False)
        # Available data columns.
        self.assertIn("Foo", res[0])
        self.assertEqual(res[0]["Foo"], False)

    def test_two_cdsa_workspaces_one_study_one_shared(self):
        available_data_1 = AvailableDataFactory.create(name="Foo")
        available_data_2 = AvailableDataFactory.create(name="Bar")
        study = StudyFactory.create(short_name="TEST")
        workspace_1 = CDSAWorkspaceFactory.create(study=study)
        workspace_1.available_data.add(available_data_1)
        WorkspaceGroupSharingFactory.create(workspace=workspace_1.workspace, group__name="PRIMED_ALL")
        workspace_2 = CDSAWorkspaceFactory.create(study=study)
        workspace_2.available_data.add(available_data_2)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 2)
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": True,
                "access_mechanism": "CDSA",
                "Foo": True,
                "Bar": False,
            },
            res,
        )
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "CDSA",
                "Foo": False,
                "Bar": True,
            },
            res,
        )

    def test_two_cdsa_workspaces(self):
        AvailableDataFactory.create(name="Foo")
        study_1 = StudyFactory.create(short_name="TEST")
        study_2 = StudyFactory.create(short_name="Other")
        CDSAWorkspaceFactory.create(study=study_1)
        CDSAWorkspaceFactory.create(study=study_2)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 2)
        self.assertIn(
            {
                "study": "Other",
                "is_shared": False,
                "access_mechanism": "CDSA",
                "Foo": False,
            },
            res,
        )
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "CDSA",
                "Foo": False,
            },
            res,
        )

    def test_one_cdsa_workspace_one_open_access_workspace_different_studies(self):
        AvailableDataFactory.create(name="Foo")
        study_1 = StudyFactory.create(short_name="TEST")
        CDSAWorkspaceFactory.create(study=study_1)
        study_2 = StudyFactory.create(short_name="Other")
        workspace = OpenAccessWorkspaceFactory.create()
        workspace.studies.add(study_2)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 2)
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "CDSA",
                "Foo": False,
            },
            res,
        )
        self.assertIn(
            {
                "study": "Other",
                "is_shared": False,
                "access_mechanism": "Open access",
                "Foo": False,
            },
            res,
        )

    def test_one_cdsa_workspace_one_open_access_workspace_same_study(self):
        AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        CDSAWorkspaceFactory.create(study=study)
        workspace = OpenAccessWorkspaceFactory.create()
        workspace.studies.add(study)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 2)
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "CDSA",
                "Foo": False,
            },
            res,
        )
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "Open access",
                "Foo": False,
            },
            res,
        )

    def test_one_cdsa_workspace_one_open_access_workspace_different_available_data(
        self,
    ):
        available_data_1 = AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        workspace = CDSAWorkspaceFactory.create(study=study)
        workspace.available_data.add(available_data_1)
        workspace = OpenAccessWorkspaceFactory.create()
        workspace.studies.add(study)
        res = helpers.get_summary_table_data()
        self.assertEqual(len(res), 2)
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "CDSA",
                "Foo": True,
            },
            res,
        )
        self.assertIn(
            {
                "study": "TEST",
                "is_shared": False,
                "access_mechanism": "Open access",
                "Foo": False,
            },
            res,
        )


class GetWorkspacesForPhenotypeInventoryTest(TestCase):
    """Tests for the helpers.get_workspaces_for_inventory method."""

    def setUp(self):
        """Set up the test case."""
        super().setUp()
        # Create the PRIMED_ALL group.
        self.primed_all_group = ManagedGroupFactory.create(name="PRIMED_ALL")

    def test_no_workspaces(self):
        """get_workspaces_for_inventory with no workspaces."""
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(res, {})

    def test_one_dbgap_workspace_not_shared(self):
        """get_workspaces_for_inventory with one dbGaP workspace."""
        dbGaPWorkspaceFactory.create()
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(res, {})

    def test_one_dbgap_workspace_shared_one_study(self):
        """get_workspaces_for_inventory with one dbGaP workspace."""
        study = StudyFactory.create(short_name="TEST")
        workspace = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-bp",
            workspace__name="test-ws",
            dbgap_study_accession__studies=[study],
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 1)
        self.assertIn("test-bp/test-ws", res)
        self.assertEqual(res["test-bp/test-ws"], "TEST")

    def test_one_dbgap_workspace_shared_two_studies(self):
        """get_workspaces_for_inventory with one dbGaP workspace."""
        study_1 = StudyFactory.create(short_name="TEST_2")
        study_2 = StudyFactory.create(short_name="TEST_1")
        study_accession = dbGaPStudyAccessionFactory.create(studies=[study_1, study_2])
        workspace = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-bp",
            workspace__name="test-ws",
            dbgap_study_accession=study_accession,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 1)
        self.assertIn("test-bp/test-ws", res)
        self.assertEqual(res["test-bp/test-ws"], "TEST_1, TEST_2")

    def test_two_dbgap_workspaces(self):
        """get_workspaces_for_inventory with two dbGaP workspaces."""
        study_1 = StudyFactory.create(short_name="TEST 1")
        workspace_1 = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-1",
            workspace__name="test-ws-1",
            dbgap_study_accession__studies=[study_1],
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_1.workspace, group=self.primed_all_group)
        study_2 = StudyFactory.create(short_name="TEST 2")
        workspace_2 = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-2",
            workspace__name="test-ws-2",
            dbgap_study_accession__studies=[study_2],
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_2.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 2)
        self.assertIn("test-bp-1/test-ws-1", res)
        self.assertEqual(res["test-bp-1/test-ws-1"], "TEST 1")
        self.assertIn("test-bp-2/test-ws-2", res)
        self.assertEqual(res["test-bp-2/test-ws-2"], "TEST 2")

    def test_one_cdsa_workspace_not_shared(self):
        """get_workspaces_for_inventory with one CDSA workspace."""
        CDSAWorkspaceFactory.create()
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(res, {})

    def test_one_cdsa_workspace_shared_one_study(self):
        """get_workspaces_for_inventory with one CDSA workspace."""
        study = StudyFactory.create(short_name="TEST")
        workspace = CDSAWorkspaceFactory.create(
            workspace__billing_project__name="test-bp",
            workspace__name="test-ws",
            study=study,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 1)
        self.assertIn("test-bp/test-ws", res)
        self.assertEqual(res["test-bp/test-ws"], "TEST")

    def test_two_cdsa_workspaces(self):
        """get_workspaces_for_inventory with two CDSA workspaces."""
        study_1 = StudyFactory.create(short_name="TEST 1")
        workspace_1 = CDSAWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-1",
            workspace__name="test-ws-1",
            study=study_1,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_1.workspace, group=self.primed_all_group)
        study_2 = StudyFactory.create(short_name="TEST 2")
        workspace_2 = CDSAWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-2",
            workspace__name="test-ws-2",
            study=study_2,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_2.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 2)
        self.assertIn("test-bp-1/test-ws-1", res)
        self.assertEqual(res["test-bp-1/test-ws-1"], "TEST 1")
        self.assertIn("test-bp-2/test-ws-2", res)
        self.assertEqual(res["test-bp-2/test-ws-2"], "TEST 2")

    def test_one_open_access_workspace_not_shared(self):
        """get_workspaces_for_inventory with one dbGaP workspace."""
        OpenAccessWorkspaceFactory.create()
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(res, {})

    def test_one_open_access_workspace_shared_no_study(self):
        """get_workspaces_for_inventory with one Open access workspace."""
        workspace = OpenAccessWorkspaceFactory.create(
            workspace__billing_project__name="test-bp",
            workspace__name="test-ws",
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 1)
        self.assertIn("test-bp/test-ws", res)
        self.assertEqual(res["test-bp/test-ws"], "")

    def test_one_open_access_workspace_shared_one_study(self):
        """get_workspaces_for_inventory with one Open access workspace."""
        study = StudyFactory.create(short_name="TEST")
        workspace = OpenAccessWorkspaceFactory.create(
            workspace__billing_project__name="test-bp",
            workspace__name="test-ws",
        )
        workspace.studies.add(study)
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 1)
        self.assertIn("test-bp/test-ws", res)
        self.assertEqual(res["test-bp/test-ws"], "TEST")

    def test_one_open_access_workspace_shared_two_studies(self):
        """get_workspaces_for_inventory with one Open access workspace."""
        study_1 = StudyFactory.create(short_name="TEST_2")
        study_2 = StudyFactory.create(short_name="TEST_1")
        workspace = OpenAccessWorkspaceFactory.create(
            workspace__billing_project__name="test-bp",
            workspace__name="test-ws",
        )
        workspace.studies.add(study_1, study_2)
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 1)
        self.assertIn("test-bp/test-ws", res)
        self.assertEqual(res["test-bp/test-ws"], "TEST_1, TEST_2")

    def test_two_open_access_workspaces(self):
        """get_workspaces_for_inventory with two Open access workspace."""
        workspace_1 = OpenAccessWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-1",
            workspace__name="test-ws-1",
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_1.workspace, group=self.primed_all_group)
        study_2 = StudyFactory.create(short_name="TEST 2")
        workspace_2 = OpenAccessWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-2",
            workspace__name="test-ws-2",
        )
        workspace_2.studies.add(study_2)
        WorkspaceGroupSharingFactory.create(workspace=workspace_2.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 2)
        self.assertIn("test-bp-1/test-ws-1", res)
        self.assertEqual(res["test-bp-1/test-ws-1"], "")
        self.assertIn("test-bp-2/test-ws-2", res)
        self.assertEqual(res["test-bp-2/test-ws-2"], "TEST 2")

    def test_multiple_workspace_types_same_study(self):
        study = StudyFactory.create(short_name="TEST")
        # dbgap
        workspace = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-dbgap",
            workspace__name="test-ws-dbgap",
            dbgap_study_accession__studies=[study],
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        # CDSA
        workspace = CDSAWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-cdsa",
            workspace__name="test-ws-cdsa",
            study=study,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        # Open access
        workspace = OpenAccessWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-open",
            workspace__name="test-ws-open",
        )
        workspace.studies.add(study)
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 3)
        self.assertIn("test-bp-dbgap/test-ws-dbgap", res)
        self.assertEqual(res["test-bp-dbgap/test-ws-dbgap"], "TEST")
        self.assertIn("test-bp-cdsa/test-ws-cdsa", res)
        self.assertEqual(res["test-bp-cdsa/test-ws-cdsa"], "TEST")
        self.assertIn("test-bp-open/test-ws-open", res)
        self.assertEqual(res["test-bp-open/test-ws-open"], "TEST")

    def test_multiple_workspace_types_separate_studies(self):
        study_1 = StudyFactory.create(short_name="TEST 1")
        # dbgap
        workspace = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-dbgap",
            workspace__name="test-ws-dbgap",
            dbgap_study_accession__studies=[study_1],
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        # CDSA
        study_2 = StudyFactory.create(short_name="TEST 2")
        workspace = CDSAWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-cdsa",
            workspace__name="test-ws-cdsa",
            study=study_2,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        # Open access
        study_3 = StudyFactory.create(short_name="TEST 3")
        workspace = OpenAccessWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-open",
            workspace__name="test-ws-open",
        )
        workspace.studies.add(study_3)
        WorkspaceGroupSharingFactory.create(workspace=workspace.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 3)
        self.assertIn("test-bp-dbgap/test-ws-dbgap", res)
        self.assertEqual(res["test-bp-dbgap/test-ws-dbgap"], "TEST 1")
        self.assertIn("test-bp-cdsa/test-ws-cdsa", res)
        self.assertEqual(res["test-bp-cdsa/test-ws-cdsa"], "TEST 2")
        self.assertIn("test-bp-open/test-ws-open", res)
        self.assertEqual(res["test-bp-open/test-ws-open"], "TEST 3")

    def test_non_consecutive_grouping(self):
        """Studies are grouped even if workspaces are listed non-consecutively."""
        # This replicates an issue seen in prod:
        # 1) there are multiple workspaces for the same set of studies
        # 2) objects are created in a specific order with specific alphabetizing.
        # The difference in behavior between sqlite and mariadb is likely due to different ordering
        # when the queryset results are returned, so debugging is tricky.
        study_1 = StudyFactory.create(short_name="TEST_2")
        study_2 = StudyFactory.create(short_name="TEST_1")
        study_accession_1 = dbGaPStudyAccessionFactory.create(dbgap_phs=964, studies=[study_1, study_2])
        study_accession_2 = dbGaPStudyAccessionFactory.create(dbgap_phs=286, studies=[study_2])
        # Two workspaces associated with study_accession_1 (with two studies)
        workspace_1_a = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-b",
            workspace__name="test-a-b_c3",
            dbgap_study_accession=study_accession_1,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_1_a.workspace, group=self.primed_all_group)
        workspace_2_a = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-a",
            workspace__name="test-a_c3",
            dbgap_study_accession=study_accession_2,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_2_a.workspace, group=self.primed_all_group)
        workspace_2_b = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-a",
            workspace__name="test-a_c4",
            dbgap_study_accession=study_accession_2,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_2_b.workspace, group=self.primed_all_group)
        workspace_2_c = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-a",
            workspace__name="test-a_c2",
            dbgap_study_accession=study_accession_2,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_2_c.workspace, group=self.primed_all_group)
        workspace_2_d = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-a",
            workspace__name="test-a_c1",
            dbgap_study_accession=study_accession_2,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_2_d.workspace, group=self.primed_all_group)
        workspace_1_b = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-b",
            workspace__name="test-a-b_c4",
            dbgap_study_accession=study_accession_1,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_1_b.workspace, group=self.primed_all_group)
        workspace_1_c = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-b",
            workspace__name="test-a-b_c1",
            dbgap_study_accession=study_accession_1,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_1_c.workspace, group=self.primed_all_group)
        workspace_1_d = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-b",
            workspace__name="test-a-b_c2",
            dbgap_study_accession=study_accession_1,
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_1_d.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 8)
        self.assertEqual(res["test-b/test-a-b_c1"], "TEST_1, TEST_2")
        self.assertEqual(res["test-b/test-a-b_c2"], "TEST_1, TEST_2")
        self.assertEqual(res["test-b/test-a-b_c3"], "TEST_1, TEST_2")
        self.assertEqual(res["test-b/test-a-b_c4"], "TEST_1, TEST_2")
        self.assertEqual(res["test-a/test-a_c1"], "TEST_1")
        self.assertEqual(res["test-a/test-a_c2"], "TEST_1")
        self.assertEqual(res["test-a/test-a_c3"], "TEST_1")
        self.assertEqual(res["test-a/test-a_c4"], "TEST_1")

    def test_order_dbgap(self):
        """dbGaPWorkspaces are ordered by billing project and workspace in results."""
        workspace_1 = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-2",
            workspace__name="test-ws-3",
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_1.workspace, group=self.primed_all_group)
        workspace_2 = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-2",
            workspace__name="test-ws-1",
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_2.workspace, group=self.primed_all_group)
        workspace_3 = dbGaPWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-1",
            workspace__name="test-ws-2",
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_3.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 3)
        self.assertEqual(list(res)[0], "test-bp-1/test-ws-2")
        self.assertEqual(list(res)[1], "test-bp-2/test-ws-1")
        self.assertEqual(list(res)[2], "test-bp-2/test-ws-3")

    def test_order_cdsa(self):
        """CDSAWorkspaces are ordered by billing project and workspace in results."""
        workspace_1 = CDSAWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-2",
            workspace__name="test-ws-3",
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_1.workspace, group=self.primed_all_group)
        workspace_2 = CDSAWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-2",
            workspace__name="test-ws-1",
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_2.workspace, group=self.primed_all_group)
        workspace_3 = CDSAWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-1",
            workspace__name="test-ws-2",
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_3.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 3)
        self.assertEqual(list(res)[0], "test-bp-1/test-ws-2")
        self.assertEqual(list(res)[1], "test-bp-2/test-ws-1")
        self.assertEqual(list(res)[2], "test-bp-2/test-ws-3")

    def test_order_open_access(self):
        """OpenAccessWorkspaces are ordered by billing project and workspace in results."""
        workspace_1 = OpenAccessWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-2",
            workspace__name="test-ws-3",
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_1.workspace, group=self.primed_all_group)
        workspace_2 = OpenAccessWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-2",
            workspace__name="test-ws-1",
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_2.workspace, group=self.primed_all_group)
        workspace_3 = OpenAccessWorkspaceFactory.create(
            workspace__billing_project__name="test-bp-1",
            workspace__name="test-ws-2",
        )
        WorkspaceGroupSharingFactory.create(workspace=workspace_3.workspace, group=self.primed_all_group)
        res = helpers.get_workspaces_for_inventory()
        self.assertEqual(len(res), 3)
        self.assertEqual(list(res)[0], "test-bp-1/test-ws-2")
        self.assertEqual(list(res)[1], "test-bp-2/test-ws-1")
        self.assertEqual(list(res)[2], "test-bp-2/test-ws-3")
