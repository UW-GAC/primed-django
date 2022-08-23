"""Test forms for the primed_anvil app."""

from anvil_consortium_manager.tests import factories as acm_factories
from django.test import TestCase

from .. import forms
from . import factories


class dbGaPWorkspaceFormTest(TestCase):
    """Tests for the dbGaPWorkspace class."""

    form_class = forms.dbGaPWorkspaceForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.workspace = acm_factories.WorkspaceFactory()

    def test_valid(self):
        """Form is valid with necessary input."""
        study_consent_group = factories.StudyConsentGroupFactory()
        form_data = {
            "study_consent_group": study_consent_group,
            "phs": 1,
            "version": 1,
            "participant_set": 1,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_study_consent_group(self):
        """Form is invalid when missing study_consent_group."""
        form_data = {
            "phs": 1,
            "version": 1,
            "participant_set": 1,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("study_consent_group", form.errors)
        self.assertEqual(len(form.errors["study_consent_group"]), 1)
        self.assertIn("required", form.errors["study_consent_group"][0])

    def test_invalid_missing_phs(self):
        """Form is invalid when missing phs."""
        study_consent_group = factories.StudyConsentGroupFactory.create()
        form_data = {
            "study_consent_group": study_consent_group,
            "version": 1,
            "participant_set": 1,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("phs", form.errors)
        self.assertEqual(len(form.errors["phs"]), 1)
        self.assertIn("required", form.errors["phs"][0])

    def test_invalid_phs_zero(self):
        """Form is invalid when phs is zero."""
        study_consent_group = factories.StudyConsentGroupFactory.create()
        form_data = {
            "study_consent_group": study_consent_group,
            "phs": 0,
            "version": 1,
            "participant_set": 1,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("phs", form.errors)
        self.assertEqual(len(form.errors["phs"]), 1)
        self.assertIn("greater than", form.errors["phs"][0])

    def test_invalid_missing_version(self):
        """Form is invalid when missing version."""
        study_consent_group = factories.StudyConsentGroupFactory.create()
        form_data = {
            "study_consent_group": study_consent_group,
            "phs": 1,
            "participant_set": 1,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("version", form.errors)
        self.assertEqual(len(form.errors["version"]), 1)
        self.assertIn("required", form.errors["version"][0])

    def test_invalid_vesrion_zero(self):
        """Form is invalid when vesrion is zero."""
        study_consent_group = factories.StudyConsentGroupFactory.create()
        form_data = {
            "study_consent_group": study_consent_group,
            "phs": 1,
            "version": 0,
            "participant_set": 1,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("version", form.errors)
        self.assertEqual(len(form.errors["version"]), 1)
        self.assertIn("greater than", form.errors["version"][0])

    def test_invalid_missing_participant_set(self):
        """Form is invalid when missing participant_set."""
        study_consent_group = factories.StudyConsentGroupFactory.create()
        form_data = {
            "study_consent_group": study_consent_group,
            "phs": 1,
            "version": 1,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("participant_set", form.errors)
        self.assertEqual(len(form.errors["participant_set"]), 1)
        self.assertIn("required", form.errors["participant_set"][0])

    def test_invalid_participant_set_zero(self):
        """Form is invalid when participant_set is zero."""
        study_consent_group = factories.StudyConsentGroupFactory.create()
        form_data = {
            "study_consent_group": study_consent_group,
            "phs": 1,
            "version": 1,
            "participant_set": 0,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("participant_set", form.errors)
        self.assertEqual(len(form.errors["participant_set"]), 1)
        self.assertIn("greater than", form.errors["participant_set"][0])

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing phs."""
        study_consent_group = factories.StudyConsentGroupFactory.create()
        form_data = {
            "study_consent_group": study_consent_group,
            "phs": 1,
            "version": 1,
            "participant_set": 1,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("workspace", form.errors)
        self.assertEqual(len(form.errors["workspace"]), 1)
        self.assertIn("required", form.errors["workspace"][0])

    def test_invalid_duplicate_object(self):
        """Form is invalid with a duplicated object."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        form_data = {
            "study_consent_group": dbgap_workspace.study_consent_group,
            "phs": dbgap_workspace.phs,
            "version": dbgap_workspace.version,
            "participant_set": dbgap_workspace.participant_set + 1,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        non_field_errors = form.non_field_errors()
        self.assertEqual(len(non_field_errors), 1)
        self.assertIn("already exists", non_field_errors[0])
