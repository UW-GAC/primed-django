"""Test forms for the `dbgap` app."""

import json

from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.test import TestCase
from faker import Faker

from primed.duo.tests.factories import DataUseModifierFactory, DataUsePermissionFactory
from primed.primed_anvil.tests.factories import AvailableDataFactory, StudyFactory
from primed.users.tests.factories import UserFactory

from .. import forms
from . import factories

fake = Faker()


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
            "dbgap_phs": 1,
            "studies": [self.study],
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_studies(self):
        """Form is invalid when missing studies."""
        form_data = {
            "dbgap_phs": 1,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("studies", form.errors)
        self.assertEqual(len(form.errors["studies"]), 1)
        self.assertIn("required", form.errors["studies"][0])

    def test_two_studies(self):
        """Form is invalid when missing studies."""
        study_2 = StudyFactory.create()
        form_data = {"dbgap_phs": 1, "studies": [self.study, study_2]}
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_empty_studies(self):
        """Form is invalid when missing studies."""
        form_data = {"dbgap_phs": 1, "studies": []}
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("studies", form.errors)
        self.assertEqual(len(form.errors["studies"]), 1)
        self.assertIn("required", form.errors["studies"][0])

    def test_invalid_missing_dbgap_phs(self):
        """Form is invalid when missing dbgap_phs."""
        form_data = {
            "studies": [self.study],
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_phs", form.errors)
        self.assertEqual(len(form.errors["dbgap_phs"]), 1)
        self.assertIn("required", form.errors["dbgap_phs"][0])

    def test_invalid_dbgap_phs_zero(self):
        """Form is invalid when dbgap_phs is zero."""
        form_data = {
            "studies": [self.study],
            "dbgap_phs": 0,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_phs", form.errors)
        self.assertEqual(len(form.errors["dbgap_phs"]), 1)
        self.assertIn("greater than", form.errors["dbgap_phs"][0])

    def test_invalid_duplicate_object(self):
        """Form is invalid with a duplicated object."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        other_study = StudyFactory.create()
        form_data = {
            "studies": [other_study],
            "dbgap_phs": dbgap_study_accession.dbgap_phs,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("dbgap_phs", form.errors)
        self.assertEqual(len(form.errors["dbgap_phs"]), 1)
        self.assertIn("already exists", form.errors["dbgap_phs"][0])


class dbGaPWorkspaceFormTest(TestCase):
    """Tests for the dbGaPWorkspaceForm class."""

    form_class = forms.dbGaPWorkspaceForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.workspace = WorkspaceFactory()
        self.dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        self.requester = UserFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_with_data_use_permission(self):
        data_use_permission = DataUsePermissionFactory.create()
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "data_use_permission": data_use_permission,
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_one_data_use_modifier(self):
        """Form is valid with necessary input."""
        data_use_permission = DataUsePermissionFactory.create()
        data_use_modifier = DataUseModifierFactory.create()
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "data_use_permission": data_use_permission,
            "data_use_modifiers": [data_use_modifier],
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_two_data_use_modifiers(self):
        """Form is valid with necessary input."""
        data_use_permission = DataUsePermissionFactory.create()
        data_use_modifiers = DataUseModifierFactory.create_batch(2)
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "data_use_permission": data_use_permission,
            "data_use_modifiers": data_use_modifiers,
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_study(self):
        """Form is invalid when missing dbgap_study_accession."""
        form_data = {
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_study_accession", form.errors)
        self.assertEqual(len(form.errors["dbgap_study_accession"]), 1)
        self.assertIn("required", form.errors["dbgap_study_accession"][0])

    def test_invalid_requester(self):
        """Form is invalid when missing requested_by."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("requested_by", form.errors)
        self.assertEqual(len(form.errors["requested_by"]), 1)
        self.assertIn("required", form.errors["requested_by"][0])

    def test_invalid_missing_gsr_restricted(self):
        """Form is invalid when missing requested_by."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            # "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("gsr_restricted", form.errors)
        self.assertEqual(len(form.errors["gsr_restricted"]), 1)
        self.assertIn("required", form.errors["gsr_restricted"][0])

    def test_invalid_missing_dbgap_version(self):
        """Form is invalid when missing dbgap_version."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_phs": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_version", form.errors)
        self.assertEqual(len(form.errors["dbgap_version"]), 1)
        self.assertIn("required", form.errors["dbgap_version"][0])

    def test_invalid_version_zero(self):
        """Form is invalid when vesrion is zero."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 0,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_participant_set", form.errors)
        self.assertEqual(len(form.errors["dbgap_participant_set"]), 1)
        self.assertIn("greater than", form.errors["dbgap_participant_set"][0])

    def test_invalid_missing_dbgap_consent_abbreviation(self):
        """Form is invalid when missing dbgap_consent_abbreviation."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "data_use_limitations": "test limitations",
            "dbgap_consent_code": 1,
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_consent_abbreviation", form.errors)
        self.assertEqual(len(form.errors["dbgap_consent_abbreviation"]), 1)
        self.assertIn("required", form.errors["dbgap_consent_abbreviation"][0])

    def test_invalid_missing_dbgap_consent_code(self):
        """Form is invalid when missing dbgap_consent_code."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "data_use_limitations": "test limitations",
            "dbgap_consent_abbreviation": "GRU",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_consent_code", form.errors)
        self.assertEqual(len(form.errors["dbgap_consent_code"]), 1)
        self.assertIn("required", form.errors["dbgap_consent_code"][0])

    def test_invalid_missing_data_use_limitations(self):
        """Form is invalid when missing data_use_limitations."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("data_use_limitations", form.errors)
        self.assertEqual(len(form.errors["data_use_limitations"]), 1)
        self.assertIn("required", form.errors["data_use_limitations"][0])

    def test_invalid_acknowledgments(self):
        """Form is invalid when missing acknowledgments."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("acknowledgments", form.errors)
        self.assertEqual(len(form.errors["acknowledgments"]), 1)
        self.assertIn("required", form.errors["acknowledgments"][0])

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing phs."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "requested_by": self.requester,
            "gsr_restricted": False,
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
            "dbgap_consent_abbreviation": dbgap_workspace.dbgap_consent_abbreviation,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        non_field_errors = form.non_field_errors()
        self.assertEqual(len(non_field_errors), 1)
        self.assertIn("already exists", non_field_errors[0])

    def test_valid_one_available_data(self):
        """Form is valid with necessary input and one available data record."""
        available_data = AvailableDataFactory.create()
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "available_data": [available_data],
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_two_available_data(self):
        """Form is valid with necessary input and two available data records."""
        available_data = AvailableDataFactory.create_batch(2)
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
            "data_use_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "workspace": self.workspace,
            "requested_by": self.requester,
            "available_data": available_data,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())


class dbGaPApplicationFormTest(TestCase):
    """Tests for the dbGaPApplicationForm class."""

    form_class = forms.dbGaPApplicationForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.pi = UserFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "principal_investigator": self.pi,
            "dbgap_project_id": 1,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_pi(self):
        """Form is invalid when missing principal_investigator."""
        form_data = {
            "dbgap_project_id": 1,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("principal_investigator", form.errors)
        self.assertEqual(len(form.errors["principal_investigator"]), 1)
        self.assertIn("required", form.errors["principal_investigator"][0])

    def test_invalid_missing_dbgap_project_id(self):
        """Form is invalid when missing phs."""
        form_data = {
            "principal_investigator": self.pi,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_project_id", form.errors)
        self.assertEqual(len(form.errors["dbgap_project_id"]), 1)
        self.assertIn("required", form.errors["dbgap_project_id"][0])

    def test_invalid_dbgap_project_id_zero(self):
        """Form is invalid when phs is zero."""
        form_data = {
            "principal_investigator": self.pi,
            "dbgap_project_id": 0,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_project_id", form.errors)
        self.assertEqual(len(form.errors["dbgap_project_id"]), 1)
        self.assertIn("greater than", form.errors["dbgap_project_id"][0])

    def test_invalid_duplicate_object(self):
        """Form is invalid with a duplicated object."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        other_pi = UserFactory.create()
        form_data = {
            "principal_investigator": other_pi,
            "dbgap_project_id": dbgap_application.dbgap_project_id,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("dbgap_project_id", form.errors)
        self.assertEqual(len(form.errors["dbgap_project_id"]), 1)
        self.assertIn("already exists", form.errors["dbgap_project_id"][0])


class dbGaPDataAccessSnapshotFormTest(TestCase):
    """Tests for the dbGaPDataAccessSnapshotForm class."""

    form_class = forms.dbGaPDataAccessSnapshotForm

    def setUp(self):
        """Create some data for use in the form."""
        self.pi = UserFactory.create()
        self.dbgap_application = factories.dbGaPApplicationFactory.create()
        # Replicate the json we expect to get from dbGaP.

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "dbgap_dar_data": json.dumps(
                [
                    factories.dbGaPJSONProjectFactory(
                        dbgap_application=self.dbgap_application
                    )
                ]
            ),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_missing_dbgap_application(self):
        """Form is invalid when dbgap_application is missing."""
        form = self.form_class(
            data={"dbgap_dar_data": json.dumps([factories.dbGaPJSONProjectFactory()])}
        )
        from django.core.exceptions import ObjectDoesNotExist

        with self.assertRaises(ObjectDoesNotExist):
            # Model clean method needs the dbgap_application...
            form.is_valid()
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_application", form.errors)
        self.assertEqual(len(form.errors["dbgap_application"]), 1)
        self.assertIn("required", form.errors["dbgap_application"][0])

    def test_dbgap_dar_data_missing(self):
        """Form is invalid when json is missing."""
        form = self.form_class(data={"dbgap_application": self.dbgap_application})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("required", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_blank(self):
        form_data = {
            "dbgap_dar_data": "",
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("required", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_zero_elements_in_array(self):
        """Form is invalid when there are no elements in the json array."""
        form_data = {
            # Get responses for two dbgap_project_ids.
            "dbgap_dar_data": "[]",
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("required", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_extra_elements(self):
        """Form is invalid when there are two elements in the json array."""
        form_data = {
            # Get responses for two dbgap_project_ids.
            "dbgap_dar_data": json.dumps(
                [
                    factories.dbGaPJSONProjectFactory(),
                    factories.dbGaPJSONProjectFactory(),
                ]
            ),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON array", form.errors["dbgap_dar_data"][0])
        self.assertIn("more than one", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_dbgap_project_id(self):
        """Form is invalid when dbgap_project_id is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory.create()
        project_json.pop("Project_id")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("Project_id", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_studies(self):
        """Form is invalid when studies is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory.create(
            dbgap_application=self.dbgap_application
        )
        project_json.pop("studies")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("studies", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_study_accession(self):
        """Form is invalid when study_accession is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory.create(
            dbgap_application=self.dbgap_application
        )
        project_json["studies"][0].pop("study_accession")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("study_accession", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_requests(self):
        """Form is invalid when requests is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory.create(
            dbgap_application=self.dbgap_application,
            studies__0__requests=[],
        )
        project_json["studies"][0].pop("requests")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("requests", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_consent_abbrev(self):
        """Form is invalid when consent_abbrev is missing from the JSON."""
        dar_json = factories.dbGaPJSONRequestFactory()
        dar_json.pop("consent_abbrev")
        project_json = factories.dbGaPJSONProjectFactory.create(
            dbgap_application=self.dbgap_application,
            studies__0__requests=[dar_json],
        )
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("consent_abbrev", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_consent_code(self):
        """Form is invalid when consent_code is missing from the JSON."""
        dar_json = factories.dbGaPJSONRequestFactory()
        dar_json.pop("consent_code")
        project_json = factories.dbGaPJSONProjectFactory.create(
            dbgap_application=self.dbgap_application,
            studies__0__requests=[dar_json],
        )
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("consent_code", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_dar(self):
        """Form is invalid when DAR is missing from the JSON."""
        dar_json = factories.dbGaPJSONRequestFactory()
        dar_json.pop("DAR")
        project_json = factories.dbGaPJSONProjectFactory.create(
            dbgap_application=self.dbgap_application,
            studies__0__requests=[dar_json],
        )
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("DAR", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_current_DAR_status(self):
        """Form is invalid when current_DAR_status is missing from the JSON."""
        dar_json = factories.dbGaPJSONRequestFactory()
        dar_json.pop("current_DAR_status")
        project_json = factories.dbGaPJSONProjectFactory.create(
            dbgap_application=self.dbgap_application,
            studies__0__requests=[dar_json],
        )
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("current_DAR_status", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_DAC_abbrev(self):
        """Form is invalid when DAC_abbrev is missing from the JSON."""
        dar_json = factories.dbGaPJSONRequestFactory()
        dar_json.pop("DAC_abbrev")
        project_json = factories.dbGaPJSONProjectFactory.create(
            dbgap_application=self.dbgap_application,
            studies__0__requests=[dar_json],
        )
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("DAC_abbrev", form.errors["dbgap_dar_data"][0])

    def test_dbgap_project_id_does_not_match(self):
        """Form is not valid when the dbgap_project_id does not match."""
        form_data = {
            "dbgap_dar_data": json.dumps(
                [factories.dbGaPJSONProjectFactory(Project_id=2)]
            ),
            "dbgap_application": self.dbgap_application,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("__all__", form.errors)
        self.assertEqual(len(form.errors["__all__"]), 1)
        self.assertIn("Project_id", form.errors["__all__"][0])


class dbGaPDataAccessSnapshotMultipleFormTest(TestCase):
    """Tests for the dbGaPDataAccessMultipleSnapshotForm class."""

    form_class = forms.dbGaPDataAccessSnapshotMultipleForm

    def test_valid_one_project(self):
        """Form is valid with necessary input."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        project_json = factories.dbGaPJSONProjectFactory(
            dbgap_application=dbgap_application
        )
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_two_projects(self):
        dbgap_application_1 = factories.dbGaPApplicationFactory.create()
        project_json_1 = factories.dbGaPJSONProjectFactory(
            dbgap_application=dbgap_application_1
        )
        dbgap_application_2 = factories.dbGaPApplicationFactory.create()
        project_json_2 = factories.dbGaPJSONProjectFactory(
            dbgap_application=dbgap_application_2
        )
        form_data = {
            "dbgap_dar_data": json.dumps([project_json_1, project_json_2]),
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_dbgap_dar_data_missing(self):
        """Form is invalid when dbgap_dar_data is missing."""
        form = self.form_class(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("required", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_blank(self):
        form_data = {
            "dbgap_dar_data": "",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("required", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_zero_elements_in_array(self):
        """Form is invalid when there are no elements in the json array."""
        form_data = {
            # Get responses for two dbgap_project_ids.
            "dbgap_dar_data": "[]",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("required", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_dbgap_project_id(self):
        """Form is invalid when dbgap_project_idis missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory()
        project_json.pop("Project_id")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("Project_id", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_studies(self):
        """Form is invalid when studies is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory()
        project_json.pop("studies")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("studies", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_study_accession(self):
        """Form is invalid when study_accession is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory()
        project_json["studies"][0].pop("study_accession")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("study_accession", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_requests(self):
        """Form is invalid when requests is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory()
        project_json["studies"][0].pop("requests")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("requests", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_consent_abbrev(self):
        """Form is invalid when consent_abbrev is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory()
        project_json["studies"][0]["requests"][0].pop("consent_abbrev")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("consent_abbrev", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_consent_code(self):
        """Form is invalid when consent_code is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory()
        project_json["studies"][0]["requests"][0].pop("consent_code")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("consent_code", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_dar(self):
        """Form is invalid when DAR is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory()
        project_json["studies"][0]["requests"][0].pop("DAR")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("DAR", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_current_DAR_status(self):
        """Form is invalid when current_DAR_status is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory()
        project_json["studies"][0]["requests"][0].pop("current_DAR_status")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("current_DAR_status", form.errors["dbgap_dar_data"][0])

    def test_dbgap_dar_data_missing_DAC_abbrev(self):
        """Form is invalid when DAC_abbrev is missing from the JSON."""
        project_json = factories.dbGaPJSONProjectFactory()
        project_json["studies"][0]["requests"][0].pop("DAC_abbrev")
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("JSON validation error:", form.errors["dbgap_dar_data"][0])
        self.assertIn("DAC_abbrev", form.errors["dbgap_dar_data"][0])

    def test_one_project_does_not_exist(self):
        project_json = factories.dbGaPJSONProjectFactory()
        form_data = {
            "dbgap_dar_data": json.dumps([project_json]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("do not exist", form.errors["dbgap_dar_data"][0])

    def test_two_projects_do_not_exist(self):
        project_json_1 = factories.dbGaPJSONProjectFactory()
        project_json_2 = factories.dbGaPJSONProjectFactory()
        form_data = {
            "dbgap_dar_data": json.dumps([project_json_1, project_json_2]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("do not exist", form.errors["dbgap_dar_data"][0])

    def test_two_projects_one_does_not_exist(self):
        dbgap_application = factories.dbGaPApplicationFactory.create()
        project_json_1 = factories.dbGaPJSONProjectFactory(
            dbgap_application=dbgap_application
        )
        project_json_2 = factories.dbGaPJSONProjectFactory()
        form_data = {
            "dbgap_dar_data": json.dumps([project_json_1, project_json_2]),
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("dbgap_dar_data", form.errors)
        self.assertEqual(len(form.errors["dbgap_dar_data"]), 1)
        self.assertIn("do not exist", form.errors["dbgap_dar_data"][0])
