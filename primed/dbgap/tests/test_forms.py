"""Test forms for the `dbgap` app."""

import json

from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.test import TestCase
from faker import Faker

from primed.primed_anvil.models import DataUseModifier
from primed.primed_anvil.tests.factories import (
    DataUseModifierFactory,
    DataUsePermissionFactory,
    StudyFactory,
)
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
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

    def test_invalid_missing_dbgap_consent_abbreviation(self):
        """Form is invalid when missing dbgap_consent_abbreviation."""
        form_data = {
            "dbgap_study_accession": self.dbgap_study_accession,
            "dbgap_version": 1,
            "dbgap_participant_set": 1,
            "data_use_limitations": "test limitations",
            "dbgap_consent_code": 1,
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
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
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
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
            "dbgap_consent_abbreviation": "GRU",
            "dbgap_consent_code": 1,
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
            "dbgap_consent_abbreviation": dbgap_workspace.dbgap_consent_abbreviation,
            "data_use_limitations": "test limitations",
            "data_use_permission": self.data_use_permission,
            "workspace": self.workspace,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        non_field_errors = form.non_field_errors()
        self.assertEqual(len(non_field_errors), 1)
        self.assertIn("already exists", non_field_errors[0])


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
            "project_id": 1,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_pi(self):
        """Form is invalid when missing principal_investigator."""
        form_data = {
            "project_id": 1,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("principal_investigator", form.errors)
        self.assertEqual(len(form.errors["principal_investigator"]), 1)
        self.assertIn("required", form.errors["principal_investigator"][0])

    def test_invalid_missing_project_id(self):
        """Form is invalid when missing phs."""
        form_data = {
            "principal_investigator": self.pi,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("project_id", form.errors)
        self.assertEqual(len(form.errors["project_id"]), 1)
        self.assertIn("required", form.errors["project_id"][0])

    def test_invalid_project_id_zero(self):
        """Form is invalid when phs is zero."""
        form_data = {
            "principal_investigator": self.pi,
            "project_id": 0,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("project_id", form.errors)
        self.assertEqual(len(form.errors["project_id"]), 1)
        self.assertIn("greater than", form.errors["project_id"][0])

    def test_invalid_duplicate_object(self):
        """Form is invalid with a duplicated object."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        other_pi = UserFactory.create()
        form_data = {
            "principal_investigator": other_pi,
            "project_id": dbgap_application.project_id,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("project_id", form.errors)
        self.assertEqual(len(form.errors["project_id"]), 1)
        self.assertIn("already exists", form.errors["project_id"][0])


class dbGaPDataAccessRequestFromJsonFormTest(TestCase):
    """Tests for the dbGaPDataAccessRequestFromJsonForm class."""

    form_class = forms.dbGaPDataAccessRequestFromJsonForm

    def setUp(self):
        """Create some data for use in the form."""
        self.pi = UserFactory.create()
        # Replicate the json we expect to get from dbGaP.

    def get_valid_dbgap_application_json(self):
        """Return a valid json string for testing."""

        valid_json = {
            "Project_id": fake.random_int(),
            "PI_name": fake.name(),
            "Project_closed": "no",
            # Two studies.
            "studies": [
                {
                    "study_name": fake.company(),
                    "study_accession": "phs{phs:06d}".format(phs=fake.random_int()),
                    # N requests per study.
                    "requests": [
                        {
                            "DAC_abbrev": fake.word(),
                            "consent_abbrev": fake.word(),
                            "consent_code": fake.random_int(),
                            "DAR": fake.random_int(),
                            "current_version": fake.random_int(),
                            "current_DAR_status": "approved",
                            "was_approved": "yes",
                        }
                        for y in range(fake.random_int(min=1, max=4))
                    ],
                }
                for x in range(fake.random_int(min=1, max=4))
            ],
        }
        return valid_json

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            # Note the get_valid_json function returns valid project_id, which is one element of what dbGaP returns.
            # Therefore we need to add []'s around it.
            "json": json.dumps([self.get_valid_dbgap_application_json()]),
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_json_missing(self):
        """Form is invalid when json is missing."""
        form = self.form_class(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("required", form.errors["json"][0])

    def test_json_blank(self):
        form_data = {"json": ""}
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("required", form.errors["json"][0])

    def test_json_zero_elements_in_array(self):
        """Form is invalid when there are no elements in the json array."""
        form_data = {
            # Get responses for two project_ids.
            "json": "[]",
        }
        form = self.form_class(data=form_data)
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("required", form.errors["json"][0])

    def test_json_extra_elements(self):
        """Form is invalid when there are two elements in the json array."""
        form_data = {
            # Get responses for two project_ids.
            "json": json.dumps(
                [
                    self.get_valid_dbgap_application_json(),
                    self.get_valid_dbgap_application_json(),
                ]
            ),
        }
        form = self.form_class(data=form_data)
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("JSON validation error:", form.errors["json"][0])
        self.assertIn("JSON array", form.errors["json"][0])
        self.assertIn("too long", form.errors["json"][0])

    def test_json_missing_project_id(self):
        """Form is invalid when project_id is missing from the JSON."""
        invalid_json = self.get_valid_dbgap_application_json()
        invalid_json.pop("Project_id")
        form_data = {
            "json": json.dumps([invalid_json]),
        }
        form = self.form_class(data=form_data)
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("JSON validation error:", form.errors["json"][0])
        self.assertIn("Project_id", form.errors["json"][0])

    def test_json_missing_studies(self):
        """Form is invalid when studies is missing from the JSON."""
        invalid_json = self.get_valid_dbgap_application_json()
        invalid_json.pop("studies")
        form_data = {
            "json": json.dumps([invalid_json]),
        }
        form = self.form_class(data=form_data)
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("JSON validation error:", form.errors["json"][0])
        self.assertIn("studies", form.errors["json"][0])

    def test_json_missing_study_accession(self):
        """Form is invalid when study_accession is missing from the JSON."""
        invalid_json = self.get_valid_dbgap_application_json()
        invalid_json["studies"][0].pop("study_accession")
        form_data = {
            "json": json.dumps([invalid_json]),
        }
        form = self.form_class(data=form_data)
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("JSON validation error:", form.errors["json"][0])
        self.assertIn("study_accession", form.errors["json"][0])

    def test_json_missing_requests(self):
        """Form is invalid when requests is missing from the JSON."""
        invalid_json = self.get_valid_dbgap_application_json()
        invalid_json["studies"][0].pop("requests")
        form_data = {
            "json": json.dumps([invalid_json]),
        }
        form = self.form_class(data=form_data)
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("JSON validation error:", form.errors["json"][0])
        self.assertIn("requests", form.errors["json"][0])

    def test_json_missing_consent_abbrev(self):
        """Form is invalid when consent_abbrev is missing from the JSON."""
        invalid_json = self.get_valid_dbgap_application_json()
        invalid_json["studies"][0]["requests"][0].pop("consent_abbrev")
        form_data = {
            "json": json.dumps([invalid_json]),
        }
        form = self.form_class(data=form_data)
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("JSON validation error:", form.errors["json"][0])
        self.assertIn("consent_abbrev", form.errors["json"][0])

    def test_json_missing_consent_code(self):
        """Form is invalid when consent_code is missing from the JSON."""
        invalid_json = self.get_valid_dbgap_application_json()
        invalid_json["studies"][0]["requests"][0].pop("consent_code")
        form_data = {
            "json": json.dumps([invalid_json]),
        }
        form = self.form_class(data=form_data)
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("JSON validation error:", form.errors["json"][0])
        self.assertIn("consent_code", form.errors["json"][0])

    def test_json_missing_dar(self):
        """Form is invalid when DAR is missing from the JSON."""
        invalid_json = self.get_valid_dbgap_application_json()
        invalid_json["studies"][0]["requests"][0].pop("DAR")
        form_data = {
            "json": json.dumps([invalid_json]),
        }
        form = self.form_class(data=form_data)
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("JSON validation error:", form.errors["json"][0])
        self.assertIn("DAR", form.errors["json"][0])

    def test_json_missing_current_DAR_status(self):
        """Form is invalid when current_DAR_status is missing from the JSON."""
        invalid_json = self.get_valid_dbgap_application_json()
        invalid_json["studies"][0]["requests"][0].pop("current_DAR_status")
        form_data = {
            "json": json.dumps([invalid_json]),
        }
        form = self.form_class(data=form_data)
        self.assertEqual(len(form.errors), 1)
        self.assertIn("json", form.errors)
        self.assertEqual(len(form.errors["json"]), 1)
        self.assertIn("JSON validation error:", form.errors["json"][0])
        self.assertIn("current_DAR_status", form.errors["json"][0])
