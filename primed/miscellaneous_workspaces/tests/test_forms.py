""""Form tests for the `workspaces` app."""

from anvil_consortium_manager.adapters.workspace import workspace_adapter_registry
from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.test import TestCase

from primed.users.tests.factories import UserFactory

from .. import forms


class SimulatedDataWorkspaceFormTest(TestCase):

    form_class = forms.SimulatedDataWorkspaceForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.workspace = WorkspaceFactory.create()
        self.requester = UserFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "workspace": self.workspace,
            "requested_by": self.requester,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing workspace."""
        form_data = {
            "requested_by": self.requester,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("workspace", form.errors)
        self.assertEqual(len(form.errors["workspace"]), 1)
        self.assertIn("required", form.errors["workspace"][0])

    def test_invalid_missing_requester(self):
        """Form is valid with necessary input."""
        form_data = {
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("requested_by", form.errors)
        self.assertEqual(len(form.errors["requested_by"]), 1)
        self.assertIn("required", form.errors["requested_by"][0])


class ConsortiumDevelWorkspaceFormTest(TestCase):

    form_class = forms.ConsortiumDevelWorkspaceForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.workspace = WorkspaceFactory.create()
        self.requester = UserFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "workspace": self.workspace,
            "requested_by": self.requester,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing workspace."""
        form_data = {
            "requested_by": self.requester,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("workspace", form.errors)
        self.assertEqual(len(form.errors["workspace"]), 1)
        self.assertIn("required", form.errors["workspace"][0])

    def test_invalid_missing_requester(self):
        """Form is valid with necessary input."""
        form_data = {
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("requested_by", form.errors)
        self.assertEqual(len(form.errors["requested_by"]), 1)
        self.assertIn("required", form.errors["requested_by"][0])


class ExampleWorkspaceFormTest(TestCase):

    form_class = forms.ExampleWorkspaceForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.workspace = WorkspaceFactory.create()
        self.requester = UserFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "workspace": self.workspace,
            "requested_by": self.requester,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing workspace."""
        form_data = {
            "requested_by": self.requester,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("workspace", form.errors)
        self.assertEqual(len(form.errors["workspace"]), 1)
        self.assertIn("required", form.errors["workspace"][0])

    def test_invalid_missing_requester(self):
        """Form is valid with necessary input."""
        form_data = {
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("requested_by", form.errors)
        self.assertEqual(len(form.errors["requested_by"]), 1)
        self.assertIn("required", form.errors["requested_by"][0])


class TemplateWorkspaceFormTest(TestCase):

    form_class = forms.TemplateWorkspaceForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.workspace = WorkspaceFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "workspace": self.workspace,
            "intended_workspace_type": "example",
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing workspace."""
        form_data = {
            "intended_workspace_type": "example",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("workspace", form.errors)
        self.assertEqual(len(form.errors["workspace"]), 1)
        self.assertIn("required", form.errors["workspace"][0])

    def test_invalid_missing_intended_workspace_type(self):
        """Form is invalid if intended_workspace_type is missing."""
        form_data = {
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("intended_workspace_type", form.errors)
        self.assertEqual(len(form.errors["intended_workspace_type"]), 1)
        self.assertIn("required", form.errors["intended_workspace_type"][0])

    def test_invalid_blank_intended_workspace_type(self):
        """Form is invalid if intended_workspace_type is missing."""
        form_data = {
            "workspace": self.workspace,
            "intended_workspace_type": "",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("intended_workspace_type", form.errors)
        self.assertEqual(len(form.errors["intended_workspace_type"]), 1)
        self.assertIn("required", form.errors["intended_workspace_type"][0])

    def test_invalid_intended_workspace_type_template(self):
        """Form is invalid if intended_workspace_type is "template"."""
        form_data = {
            "workspace": self.workspace,
            "intended_workspace_type": "template",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("intended_workspace_type", form.errors)
        self.assertEqual(len(form.errors["intended_workspace_type"]), 1)
        self.assertIn("template", form.errors["intended_workspace_type"][0])

    def test_invalid_workspace_type_unregistered_type(self):
        """Form is invalid if intended_workspace_type is not a registered type."""
        form_data = {
            "workspace": self.workspace,
            "intended_workspace_type": "foo",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("intended_workspace_type", form.errors)
        self.assertEqual(len(form.errors["intended_workspace_type"]), 1)
        self.assertIn("valid choice", form.errors["intended_workspace_type"][0])

    def test_form_all_registered_adapters(self):
        """Form is invalid if intended_workspace_type is not a registered type."""
        workspace_types = list(workspace_adapter_registry.get_registered_names().keys())
        for workspace_type in workspace_types:
            if workspace_type == "template":
                pass
            else:
                form_data = {
                    "workspace": self.workspace,
                    "intended_workspace_type": workspace_type,
                }
                form = self.form_class(data=form_data)
                self.assertTrue(form.is_valid())
