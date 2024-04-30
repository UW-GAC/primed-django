from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .. import models
from . import factories


class LoadDUOTestCase(TestCase):
    def test_error_when_data_use_permission_exists(self):
        """Raises exception when a DataUsePermission instance exists."""
        factories.DataUsePermissionFactory.create()
        with self.assertRaises(CommandError) as e:
            call_command("load_duo", duo_file="foo")
        self.assertIn("already exists", str(e.exception))
        self.assertEqual(models.DataUsePermission.objects.count(), 1)

    def test_error_when_data_use_modifier_exists(self):
        """Raises exception when a DataUseModifier instance exists."""
        factories.DataUseModifierFactory.create()
        with self.assertRaises(CommandError) as e:
            call_command("load_duo", duo_file="foo")
        self.assertIn("already exists", str(e.exception))
        self.assertEqual(models.DataUseModifier.objects.count(), 1)

    def test_command_permissions_code_not_in_ontology(self):
        """Raises exception when specified permissions-code is not in the ontology."""
        with self.assertRaises(CommandError) as e:
            call_command("load_duo", permissions_code="foo")
        self.assertIn("permissions-code 'foo' not in available terms.", str(e.exception))

    def test_command_modifiers_code_not_in_ontology(self):
        """Raises exception when specified modifiers-code is not in the ontology."""
        with self.assertRaises(CommandError) as e:
            call_command("load_duo", modifiers_code="foo")
        self.assertIn("modifiers-code 'foo' not in available terms.", str(e.exception))

    def test_loads_duo_fixture(self):
        """Loads the provided DUO fixture successfully."""
        call_command("load_duo")
        self.assertEqual(models.DataUsePermission.objects.count(), 5)
        self.assertEqual(models.DataUseModifier.objects.count(), 18)

    def test_command_output(self):
        """Correct output."""
        out = StringIO()
        call_command("load_duo", stdout=out)
        self.assertIn("5 DataUsePermissions and 18 DataUseModifiers loaded.", out.getvalue())
