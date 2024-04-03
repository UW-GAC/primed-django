""""Form tests for the `workspaces` app."""

from anvil_consortium_manager.adapters.workspace import workspace_adapter_registry
from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.test import TestCase

from primed.primed_anvil.tests.factories import AvailableDataFactory, StudyFactory
from primed.users.tests.factories import UserFactory

from .. import forms
from . import factories


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


class ResourceWorkspaceFormTest(TestCase):

    form_class = forms.ResourceWorkspaceForm

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
            "intended_usage": "Test usage",
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing workspace."""
        form_data = {
            "intended_usage": "Test usage",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("workspace", form.errors)
        self.assertEqual(len(form.errors["workspace"]), 1)
        self.assertIn("required", form.errors["workspace"][0])

    def test_invalid_missing_intended_usage(self):
        """Form is invalid if intended_workspace_type is missing."""
        form_data = {
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("intended_usage", form.errors)
        self.assertEqual(len(form.errors["intended_usage"]), 1)
        self.assertIn("required", form.errors["intended_usage"][0])

    def test_invalid_blank_intended_usage(self):
        """Form is invalid if intended_workspace_type is missing."""
        form_data = {
            "workspace": self.workspace,
            "intended_usage": "",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("intended_usage", form.errors)
        self.assertEqual(len(form.errors["intended_usage"]), 1)
        self.assertIn("required", form.errors["intended_usage"][0])


class OpenAccessWorkspaceFormTest(TestCase):

    form_class = forms.OpenAccessWorkspaceForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.workspace = WorkspaceFactory.create()
        self.requester = UserFactory.create()
        self.study = StudyFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        # available_data =
        form_data = {
            "workspace": self.workspace,
            "requested_by": self.requester,
            "studies": [self.study],
            "data_source": "test source",
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing workspace."""
        form_data = {
            "requested_by": self.requester,
            "studies": [self.study],
            "data_source": "test source",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("workspace", form.errors)
        self.assertEqual(len(form.errors["workspace"]), 1)
        self.assertIn("required", form.errors["workspace"][0])

    def test_invalid_missing_requester(self):
        """Form is invalid when missing requester."""
        form_data = {
            "workspace": self.workspace,
            "studies": [self.study],
            "data_source": "test source",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("requested_by", form.errors)
        self.assertEqual(len(form.errors["requested_by"]), 1)
        self.assertIn("required", form.errors["requested_by"][0])

    def test_invalid_missing_studies(self):
        """Form is invalid when missing studies."""
        form_data = {
            "workspace": self.workspace,
            "requested_by": self.requester,
            "data_source": "test source",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("studies", form.errors)
        self.assertEqual(len(form.errors["studies"]), 1)
        self.assertIn("required", form.errors["studies"][0])

    def test_invalid_missing_data_source(self):
        """Form is invalid when missing data_source."""
        form_data = {
            "workspace": self.workspace,
            "studies": [self.study],
            "requested_by": self.requester,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("data_source", form.errors)
        self.assertEqual(len(form.errors["data_source"]), 1)
        self.assertIn("required", form.errors["data_source"][0])

    def test_valid_two_studies(self):
        """Form is invalid when missing studies."""
        study = StudyFactory.create()
        form_data = {
            "workspace": self.workspace,
            "requested_by": self.requester,
            "studies": [self.study, study],
            "data_source": "test source",
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_one_available_data(self):
        """Form is invalid when missing studies."""
        available_data = AvailableDataFactory.create()
        form_data = {
            "workspace": self.workspace,
            "requested_by": self.requester,
            "studies": [self.study],
            "data_source": "test source",
            "available_data": [available_data],
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_two_available_data(self):
        """Form is invalid when missing studies."""
        available_data_1 = AvailableDataFactory.create()
        available_data_2 = AvailableDataFactory.create()
        form_data = {
            "workspace": self.workspace,
            "requested_by": self.requester,
            "studies": [self.study],
            "data_source": "test source",
            "available_data": [available_data_1, available_data_2],
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_data_url(self):
        """Form is valid with data_url."""
        form_data = {
            "workspace": self.workspace,
            "requested_by": self.requester,
            "studies": [self.study],
            "data_source": "test source",
            "data_url": "http://www.example.com",
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_data_url_is_not_url(self):
        """Form is invalid if data_url is not a valid url."""
        form_data = {
            "workspace": self.workspace,
            "requested_by": self.requester,
            "studies": [self.study],
            "data_source": "test source",
            "data_url": "foo_bar",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("data_url", form.errors)
        self.assertEqual(len(form.errors["data_url"]), 1)
        self.assertIn("valid URL", form.errors["data_url"][0])


class DataPrepWorkspaceFormTest(TestCase):

    form_class = forms.DataPrepWorkspaceForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.workspace = WorkspaceFactory.create()
        # Use OpenAccessData workspaces for now.
        self.target_workspace = factories.OpenAccessWorkspaceFactory.create().workspace
        self.requester = UserFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "workspace": self.workspace,
            "target_workspace": self.target_workspace,
            "requested_by": self.requester,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing workspace."""
        form_data = {
            # "workspace": self.workspace,
            "target_workspace": self.target_workspace,
            "requested_by": self.requester,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("workspace", form.errors)
        self.assertEqual(len(form.errors["workspace"]), 1)
        self.assertIn("required", form.errors["workspace"][0])

    def test_invalid_missing_target_workspace(self):
        """Form is invalid if target_workspace is missing."""
        form_data = {
            "workspace": self.workspace,
            # "target_workspace": self.target_workspace,
            "requested_by": self.requester,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("target_workspace", form.errors)
        self.assertEqual(len(form.errors["target_workspace"]), 1)
        self.assertIn("required", form.errors["target_workspace"][0])

    def test_invalid_missing_requested_by(self):
        """Form is invalid if requested_by is missing."""
        form_data = {
            "workspace": self.workspace,
            "target_workspace": self.target_workspace,
            # "requested_by": self.requester
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("requested_by", form.errors)
        self.assertEqual(len(form.errors["requested_by"]), 1)
        self.assertIn("required", form.errors["requested_by"][0])

    def test_form_all_registered_workspaces(self):
        """Form is invalid if intended_workspace_type is not a registered type."""
        workspace_types = list(workspace_adapter_registry.get_registered_names().keys())
        for workspace_type in workspace_types:
            if workspace_type == "data_prep":
                # Cannot create data prep workspaces for data prep workspace target_workspaces.
                pass
            else:
                target_workspace = WorkspaceFactory.create(
                    workspace_type=workspace_type
                )
                form_data = {
                    "workspace": self.workspace,
                    "target_workspace": target_workspace,
                    "requested_by": self.requester,
                }
                form = self.form_class(data=form_data)
                self.assertTrue(form.is_valid())
