"""Tests of helper functions in the `primed_anvil` app."""

from anvil_consortium_manager.tests.factories import WorkspaceGroupSharingFactory
from django.test import TestCase

from primed.dbgap.tests.factories import dbGaPWorkspaceFactory
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
        open_access_workspace = OpenAccessWorkspaceFactory.create()
        open_access_workspace.studies.add(study)
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

    def test_one_workspace_one_study_not_shared_with_one_available_data(self):
        available_data = AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        dbgap_workspace = dbGaPWorkspaceFactory.create(
            dbgap_study_accession__studies=[study]
        )
        dbgap_workspace.available_data.add(available_data)
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

    def test_one_workspace_one_study_not_shared_with_two_available_data(self):
        available_data_1 = AvailableDataFactory.create(name="Foo")
        available_data_2 = AvailableDataFactory.create(name="Bar")
        study = StudyFactory.create(short_name="TEST")
        dbgap_workspace = dbGaPWorkspaceFactory.create(
            dbgap_study_accession__studies=[study]
        )
        dbgap_workspace.available_data.add(available_data_1)
        dbgap_workspace.available_data.add(available_data_2)
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

    def test_one_workspace_two_studies_not_shared_no_available_data(self):
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

    def test_one_workspace_one_study_shared_no_available_data(self):
        AvailableDataFactory.create(name="Foo")
        study = StudyFactory.create(short_name="TEST")
        dbgap_workspace = dbGaPWorkspaceFactory.create(
            dbgap_study_accession__studies=[study]
        )
        WorkspaceGroupSharingFactory.create(
            workspace=dbgap_workspace.workspace, group__name="PRIMED_ALL"
        )
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

    def test_two_workspaces_one_study(self):
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

    def test_two_workspaces_one_study_one_shared(self):
        available_data_1 = AvailableDataFactory.create(name="Foo")
        available_data_2 = AvailableDataFactory.create(name="Bar")
        study = StudyFactory.create(short_name="TEST")
        dbgap_workspace_1 = dbGaPWorkspaceFactory.create(
            dbgap_study_accession__studies=[study]
        )
        dbgap_workspace_1.available_data.add(available_data_1)
        WorkspaceGroupSharingFactory.create(
            workspace=dbgap_workspace_1.workspace, group__name="PRIMED_ALL"
        )
        dbgap_workspace_2 = dbGaPWorkspaceFactory.create(
            dbgap_study_accession__studies=[study]
        )
        dbgap_workspace_2.available_data.add(available_data_2)
        res = helpers.get_summary_table_data()
        print(res)
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

    def test_two_workspaces_multiple_studies(self):
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
        open_access_workspace = OpenAccessWorkspaceFactory.create()
        open_access_workspace.studies.add(study_2)
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
        open_access_workspace = OpenAccessWorkspaceFactory.create()
        open_access_workspace.studies.add(study)
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
        dbgap_workspace = dbGaPWorkspaceFactory.create(
            dbgap_study_accession__studies=[study]
        )
        dbgap_workspace.available_data.add(available_data_1)
        open_access_workspace = OpenAccessWorkspaceFactory.create()
        open_access_workspace.studies.add(study)
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
