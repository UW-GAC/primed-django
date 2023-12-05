from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.core.exceptions import NON_FIELD_ERRORS
from django.test import TestCase

from primed.users.tests.factories import UserFactory

from .. import forms


class CollaborativeAnalysisWorkspaceFormTest(TestCase):
    """Tests for the CollaborativeAnalysisWorkspaceForm class."""

    form_class = forms.CollaborativeAnalysisWorkspaceForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.custodian = UserFactory.create()
        self.workspace = WorkspaceFactory.create()
        self.source_workspace = WorkspaceFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "purpose": "test",
            "source_workspaces": [self.source_workspace],
            "custodian": self.custodian,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_with_proposal_id(self):
        form_data = {
            "purpose": "test",
            "proposal_id": 1,
            "source_workspaces": [self.source_workspace],
            "custodian": self.custodian,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_with_proposal_id_blank(self):
        form_data = {
            "purpose": "test",
            "proposal_id": 1,
            "source_workspaces": [self.source_workspace],
            "custodian": self.custodian,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_with_proposal_id_character(self):
        form_data = {
            "purpose": "test",
            "proposal_id": "a",
            "source_workspaces": [self.source_workspace],
            "custodian": self.custodian,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("proposal_id", form.errors)
        self.assertEqual(len(form.errors["proposal_id"]), 1)
        self.assertIn("whole number", form.errors["proposal_id"][0])

    def test_valid_two_source_workspaces(self):
        """Form is valid with necessary input."""
        source_workspace_2 = WorkspaceFactory.create()
        form_data = {
            "purpose": "test",
            "source_workspaces": [self.source_workspace, source_workspace_2],
            "custodian": self.custodian,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_purpose(self):
        """Form is invalid when missing source_workspaces."""
        form_data = {
            # "purpose": "test",
            "source_workspaces": [self.source_workspace],
            "custodian": self.custodian,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("purpose", form.errors)
        self.assertEqual(len(form.errors["purpose"]), 1)
        self.assertIn("required", form.errors["purpose"][0])

    def test_invalid_missing_source_workspaces(self):
        """Form is invalid when missing source_workspaces."""
        form_data = {
            "purpose": "test",
            # "source_workspaces": [self.source_workspace],
            "custodian": self.custodian,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("source_workspaces", form.errors)
        self.assertEqual(len(form.errors["source_workspaces"]), 1)
        self.assertIn("required", form.errors["source_workspaces"][0])

    def test_invalid_same_workspace_and_source_workspace(self):
        """Form is invalid when missing source_workspaces."""
        form_data = {
            "purpose": "test",
            "source_workspaces": [self.workspace],
            "custodian": self.custodian,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn(NON_FIELD_ERRORS, form.errors)
        self.assertEqual(len(form.errors[NON_FIELD_ERRORS]), 1)
        self.assertIn("cannot include workspace", form.errors[NON_FIELD_ERRORS][0])

    def test_invalid_custodian(self):
        """Form is invalid when missing custodian."""
        form_data = {
            "purpose": "test",
            "source_workspaces": [self.source_workspace],
            # "custodian": self.custodian,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("custodian", form.errors)
        self.assertEqual(len(form.errors["custodian"]), 1)
        self.assertIn("required", form.errors["custodian"][0])

    def test_invalid_workspace(self):
        """Form is invalid when missing workspace."""
        form_data = {
            "purpose": "test",
            "source_workspaces": [self.source_workspace],
            "custodian": self.custodian,
            # "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("workspace", form.errors)
        self.assertEqual(len(form.errors["workspace"]), 1)
        self.assertIn("required", form.errors["workspace"][0])

    # def test_source_workspace_types(self):
    #     pass
