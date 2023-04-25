"""Tests for the tables in the `cdsa` app."""

from django.test import TestCase

from .. import models, tables
from . import factories


class SignedAgreementTableTest(TestCase):
    model = models.SignedAgreement
    table_class = tables.SignedAgreementTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        factories.MemberAgreementFactory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        factories.MemberAgreementFactory.create()
        factories.DataAffiliateAgreementFactory.create()
        factories.NonDataAffiliateAgreementFactory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)

    # def test_number_workspaces(self):
    #     """Table shows correct count for number of workspaces."""
    #     self.model_factory.create()
    #     dbgap_study_accession_2 = self.model_factory.create()
    #     factories.dbGaPWorkspaceFactory.create(
    #         dbgap_study_accession=dbgap_study_accession_2
    #     )
    #     dbgap_study_accession_3 = self.model_factory.create()
    #     factories.dbGaPWorkspaceFactory.create_batch(
    #         2, dbgap_study_accession=dbgap_study_accession_3
    #     )
    #     table = self.table_class(self.model.objects.all())
    #     self.assertEqual(table.rows[0].get_cell("number_workspaces"), 0)
    #     self.assertEqual(table.rows[1].get_cell("number_workspaces"), 1)
    #     self.assertEqual(table.rows[2].get_cell("number_workspaces"), 2)
