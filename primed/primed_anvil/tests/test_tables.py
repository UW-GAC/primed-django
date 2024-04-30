from anvil_consortium_manager.models import Account
from anvil_consortium_manager.tests.factories import (
    AccountFactory,
    GroupAccountMembershipFactory,
    WorkspaceFactory,
    WorkspaceGroupSharingFactory,
)
from django.core.exceptions import ImproperlyConfigured
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

    def test_ordering(self):
        """Studies are ordered alphabetically by short name"""
        study_foo = self.model_factory.create(short_name="foo", full_name="AAA")
        study_bar = self.model_factory.create(short_name="bar", full_name="BBB")
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], study_bar)
        self.assertEqual(table.data[1], study_foo)


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

    def test_ordering(self):
        """Studies are ordered alphabetically by short name"""
        foo = self.model_factory.create(short_name="foo", full_name="AAA")
        bar = self.model_factory.create(short_name="bar", full_name="BBB")
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], bar)
        self.assertEqual(table.data[1], foo)


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

    def test_ordering(self):
        """Instances are ordered alphabetically name."""
        foo = self.model_factory.create(name="foo", description="AAA")
        bar = self.model_factory.create(name="bar", description="BBB")
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], bar)
        self.assertEqual(table.data[1], foo)


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


class BooleanIconColumnTest(TestCase):
    """Tests for the BooleanIconColumn class."""

    def test_render_default(self):
        """render method with defaults."""
        column = tables.BooleanIconColumn()
        value = column.render(True, None, None)
        self.assertIn("bi-check-circle-fill", value)
        self.assertIn("green", value)
        value = column.render(False, None, None)
        self.assertEqual(value, "")

    def test_render_show_false_icon(self):
        """render method with defaults."""
        column = tables.BooleanIconColumn(show_false_icon=True)
        value = column.render(True, None, None)
        self.assertIn("bi-check-circle-fill", value)
        self.assertIn("green", value)
        value = column.render(False, None, None)
        self.assertIn("bi-x-circle-fill", value)
        self.assertIn("red", value)

    def test_true_color(self):
        column = tables.BooleanIconColumn(true_color="blue")
        value = column.render(True, None, None)
        self.assertIn("bi-check-circle-fill", value)
        self.assertIn("blue", value)
        value = column.render(False, None, None)
        self.assertEqual(value, "")

    def test_true_icon(self):
        column = tables.BooleanIconColumn(true_icon="dash")
        value = column.render(True, None, None)
        self.assertIn("bi-dash", value)
        self.assertIn("green", value)
        value = column.render(False, None, None)
        self.assertEqual(value, "")

    def test_false_color(self):
        column = tables.BooleanIconColumn(show_false_icon=True, false_color="blue")
        value = column.render(False, None, None)
        self.assertIn("bi-x-circle-fill", value)
        self.assertIn("blue", value)
        value = column.render(True, None, None)
        self.assertIn("bi-check-circle-fill", value)
        self.assertIn("green", value)

    def test_false_icon(self):
        column = tables.BooleanIconColumn(show_false_icon=True, false_icon="dash")
        value = column.render(False, None, None)
        self.assertIn("bi-dash", value)
        self.assertIn("red", value)
        value = column.render(True, None, None)
        self.assertIn("bi-check-circle-fill", value)
        self.assertIn("green", value)


class WorkspaceSharedWithConsortiumColumnTest(TestCase):
    """Tests for the WorkspaceSharedWithConsortiumColumn class."""

    def test_render_is_not_shared(self):
        workspace = WorkspaceFactory.create()
        column = tables.WorkspaceSharedWithConsortiumColumn()
        value = column.render(None, workspace, None)
        self.assertEqual("", value)

    def test_render_is_shared(self):
        workspace = WorkspaceFactory.create()
        WorkspaceGroupSharingFactory.create(workspace=workspace, group__name="PRIMED_ALL")
        column = tables.WorkspaceSharedWithConsortiumColumn()
        value = column.render(None, workspace, None)
        self.assertIn("bi-check-circle-fill", value)
        self.assertIn("green", value)

    def test_render_is_shared_with_different_group(self):
        workspace = WorkspaceFactory.create()
        WorkspaceGroupSharingFactory.create(workspace=workspace, group__name="other")
        column = tables.WorkspaceSharedWithConsortiumColumn()
        value = column.render(None, workspace, None)
        self.assertEqual("", value)

    def test_render_not_workspace(self):
        column = tables.WorkspaceSharedWithConsortiumColumn()
        with self.assertRaises(ImproperlyConfigured):
            column.render(None, "foo", None)
