from anvil_consortium_manager.models import Account
from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    GroupAccountMembershipFactory,
)
from django.test import TestCase

from primed.users.tests.factories import UserFactory

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


class StudySiteTableTest(TestCase):
    model = models.StudySite
    model_factory = factories.StudySiteFactory
    table_class = tables.StudySiteTable

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


class AccountTableTest(TestCase):
    """Tests for the custom AccountTable."""

    model = Account
    model_factory = AccountFactory
    table_class = tables.AccountTable

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

    def test_row_with_linked_user(self):
        """Renders properly when a user is linked."""
        user = UserFactory.create()
        self.model_factory.create(user=user, verified=True)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_with_no_linked_user(self):
        """Renders properly when a user is not linked."""
        self.model_factory.create(user=None)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_number_groups(self):
        self.model_factory.create()
        account_1 = self.model_factory.create()
        account_2 = self.model_factory.create()
        GroupAccountMembershipFactory.create_batch(1, account=account_1)
        GroupAccountMembershipFactory.create_batch(2, account=account_2)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_groups"), 0)
        self.assertEqual(table.rows[1].get_cell("number_groups"), 1)
        self.assertEqual(table.rows[2].get_cell("number_groups"), 2)


class AvailableDataTableTest(TestCase):
    model = models.AvailableData
    model_factory = factories.AvailableDataFactory
    table_class = tables.AvailableDataTable

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


class DataSummaryTableTest(TestCase):

    table_class = tables.DataSummaryTable

    def test_row_count_with_no_objects(self):
        table = self.table_class([])
        self.assertEqual(len(table.rows), 0)

    def test_adds_one_available_data_column(self):
        factories.AvailableDataFactory.create(name="Foo")
        table = self.table_class([])
        self.assertEqual(table.columns[3].name, "Foo")

    def test_adds_two_available_data_column(self):
        factories.AvailableDataFactory.create(name="Foo")
        factories.AvailableDataFactory.create(name="Bar")
        table = self.table_class([])
        self.assertEqual(table.columns[3].name, "Bar")
        self.assertEqual(table.columns[4].name, "Foo")


class BooleanCheckColumnTest(TestCase):
    def test_render_available_data(self):
        factories.AvailableDataFactory.create(name="Foo")
        self.assertIn(
            "bi-check-circle-fill", tables.BooleanCheckColumn().render(True, None, None)
        )
        self.assertEqual(tables.BooleanCheckColumn().render(False, None, None), "")
