"""Tests for the tables in the `cdsa` app."""

from anvil_consortium_manager.tests.factories import GroupAccountMembershipFactory
from django.test import TestCase

from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory

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


class MemberAgreementTableTest(TestCase):
    model = models.MemberAgreement
    model_factory = factories.MemberAgreementFactory
    table_class = tables.MemberAgreementTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        self.model_factory.create_batch(3)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)

    def test_number_accessors(self):
        """Table shows correct count for number of accessors."""
        self.model_factory.create()
        obj = self.model_factory.create()
        GroupAccountMembershipFactory.create(
            group=obj.signed_agreement.anvil_access_group
        )
        obj_2 = self.model_factory.create()
        GroupAccountMembershipFactory.create_batch(
            2, group=obj_2.signed_agreement.anvil_access_group
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_accessors"), 0)
        self.assertEqual(table.rows[1].get_cell("number_accessors"), 1)
        self.assertEqual(table.rows[2].get_cell("number_accessors"), 2)


class DataAffiliateAgreementTableTest(TestCase):
    model = models.DataAffiliateAgreement
    model_factory = factories.DataAffiliateAgreementFactory
    table_class = tables.DataAffiliateAgreementTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        self.model_factory.create_batch(3)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)

    def test_number_accessors(self):
        """Table shows correct count for number of accessors."""
        self.model_factory.create()
        obj = self.model_factory.create()
        GroupAccountMembershipFactory.create(
            group=obj.signed_agreement.anvil_access_group
        )
        obj_2 = self.model_factory.create()
        GroupAccountMembershipFactory.create_batch(
            2, group=obj_2.signed_agreement.anvil_access_group
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_accessors"), 0)
        self.assertEqual(table.rows[1].get_cell("number_accessors"), 1)
        self.assertEqual(table.rows[2].get_cell("number_accessors"), 2)


class NonDataAffiliateAgreementTableTest(TestCase):
    model = models.NonDataAffiliateAgreement
    model_factory = factories.NonDataAffiliateAgreementFactory
    table_class = tables.NonDataAffiliateAgreementTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        self.model_factory.create_batch(3)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)

    def test_number_accessors(self):
        """Table shows correct count for number of accessors."""
        self.model_factory.create()
        obj = self.model_factory.create()
        GroupAccountMembershipFactory.create(
            group=obj.signed_agreement.anvil_access_group
        )
        obj_2 = self.model_factory.create()
        GroupAccountMembershipFactory.create_batch(
            2, group=obj_2.signed_agreement.anvil_access_group
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_accessors"), 0)
        self.assertEqual(table.rows[1].get_cell("number_accessors"), 1)
        self.assertEqual(table.rows[2].get_cell("number_accessors"), 2)


class RepresentativeRecordsTableTest(TestCase):
    """Tests for the RepresentativeRecordsTable class."""

    model = models.SignedAgreement
    table_class = tables.RepresentativeRecordsTable

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

    def test_render_signing_group(self):
        table = self.table_class(self.model.objects.all())
        # Members.
        study_site = StudySiteFactory.create(short_name="Test Site")
        record = factories.MemberAgreementFactory(study_site=study_site)
        self.assertEqual(
            table.render_signing_group(record.signed_agreement), "Test Site"
        )
        # Data affiliates.
        study = StudyFactory.create(short_name="Test Study")
        record = factories.DataAffiliateAgreementFactory(study=study)
        self.assertEqual(
            table.render_signing_group(record.signed_agreement), "Test Study"
        )
        # Non-data affiliates.
        record = factories.NonDataAffiliateAgreementFactory(affiliation="Test Affil")
        self.assertEqual(
            table.render_signing_group(record.signed_agreement), "Test Affil"
        )


class StudyRecordsTableTest(TestCase):
    """Tests for the StudyRecordsTable class."""

    model = models.DataAffiliateAgreement
    model_factory = factories.DataAffiliateAgreementFactory
    table_class = tables.StudyRecordsTable

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
