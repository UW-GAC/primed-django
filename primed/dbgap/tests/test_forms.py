"""Test forms for the `dbgap` app."""

from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.test import TestCase

from primed.primed_anvil.models import DataUseModifier
from primed.primed_anvil.tests.factories import (
    DataUseModifierFactory,
    DataUsePermissionFactory,
    StudyFactory,
)

from .. import forms
from . import factories


class dbGaPStudyAccessionFormTest(TestCase):
    """Tests for the dbGaPStudyAccessionForm class."""

    form_class = forms.dbGaPStudyAccessionForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.study = StudyFactory.create()
        self.data_use_permission = DataUsePermissionFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "phs": 1,
            "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_study(self):
        """Form is invalid when missing study."""
        form_data = {
            "phs": 1,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("study", form.errors)
        self.assertEqual(len(form.errors["study"]), 1)
        self.assertIn("required", form.errors["study"][0])

    def test_invalid_missing_phs(self):
        """Form is invalid when missing phs."""
        form_data = {
            "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("phs", form.errors)
        self.assertEqual(len(form.errors["phs"]), 1)
        self.assertIn("required", form.errors["phs"][0])

    def test_invalid_phs_zero(self):
        """Form is invalid when phs is zero."""
        form_data = {
            "study": self.study,
            "phs": 0,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("phs", form.errors)
        self.assertEqual(len(form.errors["phs"]), 1)
        self.assertIn("greater than", form.errors["phs"][0])

    def test_invalid_duplicate_object(self):
        """Form is invalid with a duplicated object."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        other_study = StudyFactory.create()
        form_data = {
            "study": other_study,
            "phs": dbgap_study_accession.phs,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("phs", form.errors)
        self.assertEqual(len(form.errors["phs"]), 1)
        self.assertIn("already exists", form.errors["phs"][0])


class dbGaPWorkspaceFormTest(TestCase):
    """Tests for the dbGaPWorkspaceForm class."""

    form_class = forms.dbGaPWorkspaceForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.workspace = WorkspaceFactory()
        self.dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        self.data_use_permission = DataUsePermissionFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "full_consent_code": "GRU",
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_one_data_use_modifier(self):
        """Form is valid with necessary input."""
        DataUseModifierFactory.create()
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "full_consent_code": "GRU",
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
            "data_use_modifiers": DataUseModifier.objects.all(),
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_two_data_use_modifiers(self):
        """Form is valid with necessary input."""
        DataUseModifierFactory.create_batch(2)
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "full_consent_code": "GRU",
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
            "data_use_modifiers": DataUseModifier.objects.all(),
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_study(self):
        """Form is invalid when missing dbgap_study_accession."""
        form_data = {
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "full_consent_code": "GRU",
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_study_accession", form.errors)
        self.assertEqual(len(form.errors["dbgap_study_accession"]), 1)
        self.assertIn("required", form.errors["dbgap_study_accession"][0])

    def test_invalid_missing_dbgap_version(self):
        """Form is invalid when missing dbgap_version."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "phs": 1,
            "dbgap_participant_set": 1,
            "full_consent_code": "GRU",
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_version", form.errors)
        self.assertEqual(len(form.errors["dbgap_version"]), 1)
        self.assertIn("required", form.errors["dbgap_version"][0])

    def test_invalid_vesrion_zero(self):
        """Form is invalid when vesrion is zero."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 0,
            "dbgap_participant_set": 1,
            "full_consent_code": "GRU",
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_version", form.errors)
        self.assertEqual(len(form.errors["dbgap_version"]), 1)
        self.assertIn("greater than", form.errors["dbgap_version"][0])

    def test_invalid_missing_dbgap_participant_set(self):
        """Form is invalid when missing dbgap_participant_set."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "full_consent_code": "GRU",
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_participant_set", form.errors)
        self.assertEqual(len(form.errors["dbgap_participant_set"]), 1)
        self.assertIn("required", form.errors["dbgap_participant_set"][0])

    def test_invalid_dbgap_participant_set_zero(self):
        """Form is invalid when dbgap_participant_set is zero."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 0,
            "full_consent_code": "GRU",
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_participant_set", form.errors)
        self.assertEqual(len(form.errors["dbgap_participant_set"]), 1)
        self.assertIn("greater than", form.errors["dbgap_participant_set"][0])

    def test_invalid_missing_full_consent_code(self):
        """Form is invalid when missing full_consent_code."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("full_consent_code", form.errors)
        self.assertEqual(len(form.errors["full_consent_code"]), 1)
        self.assertIn("required", form.errors["full_consent_code"][0])

    def test_invalid_missing_data_use_limitations(self):
        """Form is invalid when missing data_use_limitations."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "full_consent_code": "GRU",
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("data_use_limitations", form.errors)
        self.assertEqual(len(form.errors["data_use_limitations"]), 1)
        self.assertIn("required", form.errors["data_use_limitations"][0])

    def test_invalid_missing_data_use_permissions(self):
        """Form is invalid when missing dbgap_participant_set."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "full_consent_code": "GRU",
            "data_use_permission": "",
            "data_use_limitations": "test limitations",
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("data_use_permission", form.errors)
        self.assertEqual(len(form.errors["data_use_permission"]), 1)
        self.assertIn("required", form.errors["data_use_permission"][0])

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing phs."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "full_consent_code": "GRU",
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
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
            "dbgap_study_accession": dbgap_workspace.dbgap_study_accession,
            "dbgap_version": dbgap_workspace.dbgap_version,
            "dbgap_participant_set": dbgap_workspace.dbgap_participant_set + 1,
            "full_consent_code": dbgap_workspace.full_consent_code,
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        non_field_errors = form.non_field_errors()
        self.assertEqual(len(non_field_errors), 1)
        self.assertIn("already exists", non_field_errors[0])
