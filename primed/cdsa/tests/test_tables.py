"""Tests for the tables in the `cdsa` app."""

from anvil_consortium_manager.tests.factories import GroupAccountMembershipFactory
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

    def test_number_accessors(self):
        """Table shows correct count for number of accessors."""
        factories.MemberAgreementFactory.create()
        obj = factories.MemberAgreementFactory.create()
        GroupAccountMembershipFactory.create(
            group=obj.signed_agreement.anvil_access_group
        )
        obj_2 = factories.MemberAgreementFactory.create()
        GroupAccountMembershipFactory.create_batch(
            2, group=obj_2.signed_agreement.anvil_access_group
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_accessors"), 0)
        self.assertEqual(table.rows[1].get_cell("number_accessors"), 1)
        self.assertEqual(table.rows[2].get_cell("number_accessors"), 2)
