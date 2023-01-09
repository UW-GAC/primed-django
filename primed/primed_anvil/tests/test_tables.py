from anvil_consortium_manager.models import Account
from anvil_consortium_manager.tests.factories import AccountFactory
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
