"""Tests of models in the `dbgap` app."""

import jsonschema
import responses
from anvil_consortium_manager.tests.factories import (
    ManagedGroupFactory,
    WorkspaceFactory,
)
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import TestCase
from faker import Faker

from primed.primed_anvil.tests.factories import DataUsePermissionFactory, StudyFactory
from primed.users.tests.factories import UserFactory

from .. import models
from . import factories

fake = Faker()


class dbGaPStudyAccessionTest(TestCase):
    """Tests for the dbGaPStudyAccession model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        study = StudyFactory.create()
        instance = models.dbGaPStudyAccession(
            study=study,
            phs=1,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPStudyAccession)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPStudyAccessionFactory.create(
            study__short_name="FOO",
            phs=1,
        )
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "phs000001 - FOO")

    def test_get_absolute_url(self):
        """get_absolute_url method works correctly."""
        instance = factories.dbGaPStudyAccessionFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)

    def test_unique_dbgap_study_accession(self):
        """Saving a duplicate model fails."""
        obj = factories.dbGaPStudyAccessionFactory.create()
        study = StudyFactory.create()
        instance = factories.dbGaPStudyAccessionFactory.build(
            study=study,
            phs=obj.phs,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("phs", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["phs"]), 1)
        self.assertIn("already exists", e.exception.error_dict["phs"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_study_protect(self):
        """Cannot delete a Study if it has an associated dbGaPWorkspace."""
        study = StudyFactory.create()
        factories.dbGaPStudyAccessionFactory.create(study=study)
        with self.assertRaises(ProtectedError):
            study.delete()

    def test_phs_cannot_be_zero(self):
        """phs cannot be zero."""
        study = StudyFactory.create()
        instance = factories.dbGaPStudyAccessionFactory.build(
            study=study,
            phs=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("phs", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["phs"]), 1)
        self.assertIn(
            "greater than or equal to 1", e.exception.error_dict["phs"][0].messages[0]
        )

    def test_phs_cannot_be_negative(self):
        """phs cannot be negative."""
        study = StudyFactory.create()
        instance = factories.dbGaPStudyAccessionFactory.build(
            study=study,
            phs=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("phs", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["phs"]), 1)
        self.assertIn(
            "greater than or equal to 1", e.exception.error_dict["phs"][0].messages[0]
        )

    @responses.activate
    def test_dbgap_get_current_full_accession_numbers(self):
        """dbgap_get_current_full_accession_numbers returns correct information."""
        study_accession = factories.dbGaPStudyAccessionFactory.create(phs=3)
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs{phs:06d}.v{v}.p{p}".format(phs=3, v=29, p=5)
            },
        )
        expected_dict = {"phs": 3, "version": 29, "participant_set": 5}
        self.assertEqual(
            study_accession.dbgap_get_current_full_accession_numbers(), expected_dict
        )


class dbGaPWorkspaceTest(TestCase):
    """Tests for the dbGaPWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        data_use_permission = DataUsePermissionFactory.create()
        instance = models.dbGaPWorkspace(
            workspace=workspace,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_version=1,
            dbgap_participant_set=1,
            data_use_limitations="test limitations",
            dbgap_consent_code=1,
            dbgap_consent_abbreviation="GRU-NPU",
            data_use_permission=data_use_permission,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPWorkspace)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession__phs=1,
            dbgap_version=2,
            dbgap_participant_set=3,
            dbgap_consent_abbreviation="GRU-NPU",
        )
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "phs000001.v2.p3 - GRU-NPU")

    def test_unique_dbgap_workspace(self):
        """Saving a duplicate model fails."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        workspace = WorkspaceFactory.create()
        data_use_permission = DataUsePermissionFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study_accession=dbgap_workspace.dbgap_study_accession,
            dbgap_version=dbgap_workspace.dbgap_version,
            dbgap_consent_abbreviation=dbgap_workspace.dbgap_consent_abbreviation,
            # These are here to prevent ValueErrors about unsaved related objects.
            data_use_permission=data_use_permission,
            workspace=workspace,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("__all__", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["__all__"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["__all__"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_dbgap_study_accession_protect(self):
        """Cannot delete a dbGaPStudyAccession if it has an associated dbGaPWorkspace."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession=dbgap_study_accession
        )
        with self.assertRaises(ProtectedError):
            dbgap_study_accession.delete()

    def test_dbgap_version_cannot_be_zero(self):
        """dbgap_version cannot be zero."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study_accession=dbgap_study_accession,
            dbgap_version=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_version", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_version"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_version"][0].messages[0],
        )

    def test_dbgap_version_cannot_be_negative(self):
        """dbgap_version cannot be negative."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study_accession=dbgap_study_accession,
            dbgap_version=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_version", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_version"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_version"][0].messages[0],
        )

    def test_dbgap_participant_cannot_be_zero(self):
        """dbgap_version cannot be zero."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study_accession=dbgap_study_accession,
            dbgap_participant_set=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_participant_set", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_participant_set"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_participant_set"][0].messages[0],
        )

    def test_dbgap_participant_set_cannot_be_negative(self):
        """dbgap_version cannot be negative."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study_accession=dbgap_study_accession,
            dbgap_participant_set=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_participant_set", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_participant_set"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_participant_set"][0].messages[0],
        )

    def test_dbgap_consent_code_cannot_be_zero(self):
        """dbgap_consent_code cannot be zero."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study_accession=dbgap_study_accession,
            dbgap_consent_code=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_consent_code", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_consent_code"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_consent_code"][0].messages[0],
        )

    def test_dbgap_consent_code_cannot_be_negative(self):
        """dbgap_consent_code cannot be negative."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study_accession=dbgap_study_accession,
            dbgap_consent_code=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_consent_code", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_consent_code"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_consent_code"][0].messages[0],
        )

    def test_get_dbgap_accession(self):
        """`get_dbgap_accession` returns the correct string"""
        instance = factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession__phs=1, dbgap_version=2, dbgap_participant_set=3
        )
        self.assertEqual(instance.get_dbgap_accession(), "phs000001.v2.p3")


class dbGaPApplicationTest(TestCase):
    """Tests for the dbGaPApplication model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        pi = UserFactory.create()
        anvil_group = ManagedGroupFactory.create()
        instance = models.dbGaPApplication(
            principal_investigator=pi,
            project_id=1,
            anvil_group=anvil_group,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPApplication)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPApplicationFactory.create(
            project_id=1,
        )
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "1")

    def test_get_absolute_url(self):
        """get_absolute_url method works correctly."""
        instance = factories.dbGaPApplicationFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)

    def test_unique_dbgap_application(self):
        """Saving a duplicate model fails."""
        obj = factories.dbGaPApplicationFactory.create()
        pi = UserFactory.create()
        anvil_group = ManagedGroupFactory.create()
        instance = factories.dbGaPApplicationFactory.build(
            principal_investigator=pi,
            project_id=obj.project_id,
            anvil_group=anvil_group,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("project_id", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["project_id"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["project_id"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_user_protect(self):
        """Cannot delete a User if it has an associated dbGaPWorkspace."""
        pi = UserFactory.create()
        factories.dbGaPApplicationFactory.create(principal_investigator=pi)
        with self.assertRaises(ProtectedError):
            pi.delete()

    def test_project_id_cannot_be_zero(self):
        """project_id cannot be zero."""
        pi = UserFactory.create()
        instance = factories.dbGaPApplicationFactory.build(
            principal_investigator=pi,
            project_id=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("project_id", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["project_id"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["project_id"][0].messages[0],
        )

    def test_phs_cannot_be_negative(self):
        """phs cannot be negative."""
        pi = UserFactory.create()
        instance = factories.dbGaPApplicationFactory.build(
            principal_investigator=pi,
            project_id=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("project_id", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["project_id"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["project_id"][0].messages[0],
        )

    def test_get_dbgap_dar_json_url(self):
        """get_dbgap_dar_json_url returns a string."""
        application = factories.dbGaPApplicationFactory.create()
        self.assertIsInstance(application.get_dbgap_dar_json_url(), str)


class dbGaPDataAccessSnapshotTest(TestCase):
    """Tests for the dbGaPApplication model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        json = {
            "Project_id": dbgap_application.project_id,
            "PI_name": fake.name(),
            "Project_closed": "no",
            "studies": [],
        }
        instance = models.dbGaPDataAccessSnapshot(
            dbgap_application=dbgap_application,
            dbgap_dar_data=json,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPDataAccessSnapshot)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPDataAccessSnapshotFactory.create()
        self.assertIsInstance(instance.__str__(), str)

    def test_clean_invalid_json(self):
        """Creation using the model constructor and .save() works."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        json = {
            "PI_name": fake.name(),
            "Project_closed": "no",
            "studies": [],
        }
        instance = factories.dbGaPDataAccessSnapshotFactory.build(
            dbgap_application=dbgap_application,
            dbgap_dar_data=json,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_dar_data", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_dar_data"]), 1)
        self.assertIn(
            "required property",
            e.exception.error_dict["dbgap_dar_data"][0].messages[0],
        )

    def test_dbgap_application_protect(self):
        """Cannot delete a dbGaPApplication if it has an associated dbGaPDataAccessSnapshot."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application
        )
        with self.assertRaises(ProtectedError):
            dbgap_application.delete()

    @responses.activate
    def test_dbgap_create_dars_from_json_one_study_one_dar(self):
        """Can create one DAR for one study."""
        study_accession = factories.dbGaPStudyAccessionFactory.create(phs=421)
        valid_json = {
            "Project_id": 6512,
            "PI_name": "Test Investigator",
            "Project_closed": "no",
            # Two studies.
            "studies": [
                {
                    "study_name": "A test study",
                    "study_accession": "phs000421",
                    # N requests per study.
                    "requests": [
                        {
                            "DAC_abbrev": "FOOBI",
                            "consent_abbrev": "GRU",
                            "consent_code": 2,
                            "DAR": 23497,
                            "current_version": 12,
                            "current_DAR_status": "approved",
                            "was_approved": "yes",
                        },
                    ],
                },
            ],
        }
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__project_id=6512,
            dbgap_dar_data=valid_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs000421.v32.p18"
            },
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 1)
        new_object = dars[0]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 23497)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_study_accession, study_accession)
        self.assertEqual(new_object.dbgap_version, 32)
        self.assertEqual(new_object.dbgap_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 2)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 1)

    @responses.activate
    def test_dbgap_create_dars_from_json_one_study_two_dars(self):
        """Can create two DARs for one study."""
        study_accession = factories.dbGaPStudyAccessionFactory.create(phs=421)
        valid_json = {
            "Project_id": 6512,
            "PI_name": "Test Investigator",
            "Project_closed": "no",
            # Two studies.
            "studies": [
                {
                    "study_name": "A test study",
                    "study_accession": "phs000421",
                    # N requests per study.
                    "requests": [
                        {
                            "DAC_abbrev": "FOOBI",
                            "consent_abbrev": "GRU",
                            "consent_code": 1,
                            "DAR": 23497,
                            "current_version": 12,
                            "current_DAR_status": "approved",
                            "was_approved": "yes",
                        },
                        {
                            "DAC_abbrev": "FOOBI",
                            "consent_abbrev": "NPU",
                            "consent_code": 2,
                            "DAR": 23498,
                            "current_version": 12,
                            "current_DAR_status": "approved",
                            "was_approved": "yes",
                        },
                    ],
                },
            ],
        }
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__project_id=6512,
            dbgap_dar_data=valid_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs000421.v32.p18"
            },
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 2)
        new_object = dars[0]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 23497)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_study_accession, study_accession)
        self.assertEqual(new_object.dbgap_version, 32)
        self.assertEqual(new_object.dbgap_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        new_object = dars[1]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertIn(new_object, dars)
        self.assertEqual(new_object.dbgap_dar_id, 23498)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_study_accession, study_accession)
        self.assertEqual(new_object.dbgap_version, 32)
        self.assertEqual(new_object.dbgap_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 2)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "NPU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 2)

    @responses.activate
    def test_dbgap_create_dars_from_json_two_studies_one_dar(self):
        """Can create one DAR for two studies."""
        study_accession_1 = factories.dbGaPStudyAccessionFactory.create(phs=421)
        study_accession_2 = factories.dbGaPStudyAccessionFactory.create(phs=896)
        valid_json = {
            "Project_id": 6512,
            "PI_name": "Test Investigator",
            "Project_closed": "no",
            # Two studies.
            "studies": [
                {
                    "study_name": "Test study 1",
                    "study_accession": "phs000421",
                    # N requests per study.
                    "requests": [
                        {
                            "DAC_abbrev": "FOOBI",
                            "consent_abbrev": "GRU",
                            "consent_code": 1,
                            "DAR": 23497,
                            "current_version": 12,
                            "current_DAR_status": "approved",
                            "was_approved": "yes",
                        },
                    ],
                },
                {
                    "study_name": "Test study 2",
                    "study_accession": "phs000896",
                    # N requests per study.
                    "requests": [
                        {
                            "DAC_abbrev": "BARBI",
                            "consent_abbrev": "DS-LD",
                            "consent_code": 1,
                            "DAR": 23498,
                            "current_version": 12,
                            "current_DAR_status": "approved",
                            "was_approved": "yes",
                        },
                    ],
                },
            ],
        }
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__project_id=6512,
            dbgap_dar_data=valid_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": "phs000421"})],
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs000421.v32.p18"
            },
        )
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": "phs000896"})],
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs000896.v2.p1"
            },
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 2)
        new_object = dars[0]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 23497)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_study_accession, study_accession_1)
        self.assertEqual(new_object.dbgap_version, 32)
        self.assertEqual(new_object.dbgap_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        new_object = dars[1]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertIn(new_object, dars)
        self.assertEqual(new_object.dbgap_dar_id, 23498)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_study_accession, study_accession_2)
        self.assertEqual(new_object.dbgap_version, 2)
        self.assertEqual(new_object.dbgap_participant_set, 1)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "DS-LD")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 2)

    @responses.activate
    def test_dbgap_create_dars_from_json_study_accession_does_not_exist(self):
        """No DARs are created when the dbGaPStudyAccession does not exist."""
        valid_json = {
            "Project_id": 6512,
            "PI_name": "Test Investigator",
            "Project_closed": "no",
            # Two studies.
            "studies": [
                {
                    "study_name": "Test study 1",
                    "study_accession": "phs000421",
                    # N requests per study.
                    "requests": [
                        {
                            "DAC_abbrev": "FOOBI",
                            "consent_abbrev": "GRU",
                            "consent_code": 1,
                            "DAR": 23497,
                            "current_version": 12,
                            "current_DAR_status": "approved",
                            "was_approved": "yes",
                        },
                    ],
                },
            ],
        }
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__project_id=6512,
            dbgap_dar_data=valid_json,
        )
        with self.assertRaises(models.dbGaPStudyAccession.DoesNotExist):
            dbgap_snapshot.create_dars_from_json()
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    def test_dbgap_create_dars_from_json_two_studies_second_study_accession_does_not_exist(
        self,
    ):
        """No DARs are created when the second study doesn't have a matching dbGaPStudyAccession."""
        factories.dbGaPStudyAccessionFactory.create(phs=421)
        valid_json = {
            "Project_id": 6512,
            "PI_name": "Test Investigator",
            "Project_closed": "no",
            # Two studies.
            "studies": [
                {
                    "study_name": "Test study 1",
                    "study_accession": "phs000421",
                    # N requests per study.
                    "requests": [
                        {
                            "DAC_abbrev": "FOOBI",
                            "consent_abbrev": "GRU",
                            "consent_code": 1,
                            "DAR": 23497,
                            "current_version": 12,
                            "current_DAR_status": "approved",
                            "was_approved": "yes",
                        },
                    ],
                },
                {
                    "study_name": "Test study 2",
                    "study_accession": "phs000896",
                    # N requests per study.
                    "requests": [
                        {
                            "DAC_abbrev": "BARBI",
                            "consent_abbrev": "DS-LD",
                            "consent_code": 1,
                            "DAR": 23498,
                            "current_version": 12,
                            "current_DAR_status": "approved",
                            "was_approved": "yes",
                        },
                    ],
                },
            ],
        }
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__project_id=6512,
            dbgap_dar_data=valid_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": "phs000421"})],
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs000421.v32.p18"
            },
        )
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": "phs000896"})],
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs000896.v2.p1"
            },
        )
        with self.assertRaises(models.dbGaPStudyAccession.DoesNotExist):
            dbgap_snapshot.create_dars_from_json()
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    def test_dbgap_create_dars_from_json_invalid_json(self):
        """JSON is validated."""
        invalid_json = {
            "Project_id": 6512,
            "PI_name": "Test Investigator",
            "Project_closed": "no",
        }
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__project_id=6512,
            dbgap_dar_data=invalid_json,
        )
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            dbgap_snapshot.create_dars_from_json()
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    def test_dbgap_create_dars_from_json_mismatched_project_id(self):
        """No dbGaPDataAccessRequests are created if project_id doesn't match."""
        factories.dbGaPStudyAccessionFactory.create(phs=421)
        valid_json = {
            "Project_id": 1,
            "PI_name": "Test Investigator",
            "Project_closed": "no",
            # Two studies.
            "studies": [
                {
                    "study_name": "A test study",
                    "study_accession": "phs000421",
                    # N requests per study.
                    "requests": [
                        {
                            "DAC_abbrev": "FOOBI",
                            "consent_abbrev": "GRU",
                            "consent_code": 2,
                            "DAR": 23497,
                            "current_version": 12,
                            "current_DAR_status": "approved",
                            "was_approved": "yes",
                        },
                    ],
                },
            ],
        }
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__project_id=6512,
            dbgap_dar_data=valid_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs000421.v32.p18"
            },
        )
        with self.assertRaises(ValueError) as e:
            dbgap_snapshot.create_dars_from_json()
        self.assertIn("project_id does not match", str(e.exception))
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    @responses.activate
    def test_does_include_dars_that_are_not_approved(self):
        """Does creates DARs with a different status than approved."""
        study_accession = factories.dbGaPStudyAccessionFactory.create(phs=421)
        valid_json = {
            "Project_id": 6512,
            "PI_name": "Test Investigator",
            "Project_closed": "no",
            # Two studies.
            "studies": [
                {
                    "study_name": "A test study",
                    "study_accession": "phs000421",
                    # N requests per study.
                    "requests": [
                        {
                            "DAC_abbrev": "FOOBI",
                            "consent_abbrev": "GRU",
                            "consent_code": 1,
                            "DAR": 23497,
                            "current_version": 12,
                            "current_DAR_status": "rejected",
                            "was_approved": "yes",
                        },
                        {
                            "DAC_abbrev": "FOOBI",
                            "consent_abbrev": "NPU",
                            "consent_code": 2,
                            "DAR": 23498,
                            "current_version": 12,
                            "current_DAR_status": "approved",
                            "was_approved": "yes",
                        },
                    ],
                },
            ],
        }
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__project_id=6512,
            dbgap_dar_data=valid_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            models.dbGaPStudyAccession.DBGAP_STUDY_URL,
            status=302,
            headers={
                "Location": models.dbGaPStudyAccession.DBGAP_STUDY_URL
                + "?study_id=phs000421.v32.p18"
            },
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 2)
        new_object = dars[0]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 23497)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_study_accession, study_accession)
        self.assertEqual(new_object.dbgap_version, 32)
        self.assertEqual(new_object.dbgap_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_object.dbgap_current_status, "rejected")
        new_object = dars[1]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 23498)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_study_accession, study_accession)
        self.assertEqual(new_object.dbgap_version, 32)
        self.assertEqual(new_object.dbgap_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 2)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "NPU")
        self.assertEqual(new_object.dbgap_current_status, "approved")


class dbGaPDataAccessRequestTest(TestCase):
    """Tests for the dbGaPDataAccessRequest model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = models.dbGaPDataAccessRequest(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_dar_id=1,
            dbgap_version=2,
            dbgap_participant_set=3,
            dbgap_consent_code=4,
            dbgap_consent_abbreviation="GRU",
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPDataAccessRequest)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_dar_id=1234,
        )
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "1234")

    # def test_get_absolute_url(self):
    #     """get_absolute_url method works correctly."""
    #     instance = factories.dbGaPDataAccessRequestFactory.create()
    #     self.assertIsInstance(instance.get_absolute_url(), str)

    def test_unique_dbgap_dar_id(self):
        """Saving a duplicate model fails."""
        obj = factories.dbGaPDataAccessRequestFactory.create()
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_dar_id=obj.dbgap_dar_id,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_dar_id", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_dar_id"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["dbgap_dar_id"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_unique_dbgap_data_access_request(self):
        """Violating the unique_dbgap_data_access_request constraint fails."""
        obj = factories.dbGaPDataAccessRequestFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=obj.dbgap_data_access_snapshot,
            dbgap_study_accession=obj.dbgap_study_accession,
            dbgap_consent_code=obj.dbgap_consent_code,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("__all__", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["__all__"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["__all__"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_unique_dbgap_data_access_dar_id(self):
        """Violating the unique_dbgap_data_access_request_dar_id constraint fails."""
        obj = factories.dbGaPDataAccessRequestFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=obj.dbgap_data_access_snapshot,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_dar_id=obj.dbgap_dar_id,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("__all__", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["__all__"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["__all__"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_dbgap_data_access_snapshot_protect(self):
        """Cannot delete a dbGaPApplication if it has an associated dbGaPDataAccessSnapshot."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=dbgap_snapshot
        )
        with self.assertRaises(ProtectedError):
            dbgap_snapshot.delete()

    def test_dbgap_study_accession_protect(self):
        """Cannot delete a dbGaPStudyAccession if it has an associated dbGaPDataAccessRequest."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_study_accession=dbgap_study_accession
        )
        with self.assertRaises(ProtectedError):
            dbgap_study_accession.delete()

    def test_dbgap_dar_id_cannot_be_zero(self):
        """dbgap_dar_id cannot be zero."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_dar_id=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_dar_id", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_dar_id"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_dar_id"][0].messages[0],
        )

    def test_dbgap_dar_id_cannot_be_negative(self):
        """dbgap_dar_id cannot be negative."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_dar_id=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_dar_id", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_dar_id"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_dar_id"][0].messages[0],
        )

    def test_dbgap_version_cannot_be_zero(self):
        """dbgap_version cannot be zero."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_version=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_version", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_version"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_version"][0].messages[0],
        )

    def test_dbgap_version_cannot_be_negative(self):
        """dbgap_version cannot be negative."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_version=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_version", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_version"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_version"][0].messages[0],
        )

    def test_dbgap_participant_set_cannot_be_zero(self):
        """dbgap_participant_set cannot be zero."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_participant_set=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_participant_set", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_participant_set"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_participant_set"][0].messages[0],
        )

    def test_dbgap_participant_set_cannot_be_negative(self):
        """dbgap_participant_set cannot be negative."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_participant_set=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_participant_set", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_participant_set"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_participant_set"][0].messages[0],
        )

    def test_dbgap_consent_code_cannot_be_zero(self):
        """consent_code cannot be zero."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_consent_code=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_consent_code", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_consent_code"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_consent_code"][0].messages[0],
        )

    def test_dbgap_consent_code_cannot_be_negative(self):
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_consent_code=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_consent_code", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_consent_code"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_consent_code"][0].messages[0],
        )

    def test_approved(self):
        """The approved manager method works as expected."""
        approved_dar = factories.dbGaPDataAccessRequestFactory.create()
        closed_dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED
        )
        rejected_dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED
        )
        expired_dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_current_status=models.dbGaPDataAccessRequest.EXPIRED
        )
        new_dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_current_status=models.dbGaPDataAccessRequest.NEW
        )
        qs = models.dbGaPDataAccessRequest.objects.approved()
        self.assertEqual(len(qs), 1)
        self.assertIn(approved_dar, qs)
        self.assertNotIn(closed_dar, qs)
        self.assertNotIn(rejected_dar, qs)
        self.assertNotIn(expired_dar, qs)
        self.assertNotIn(new_dar, qs)

    def test_get_dbgap_workspace_no_matches(self):
        """Raises DoesNotExist when there is no matching workspace."""
        dar = factories.dbGaPDataAccessRequestFactory.create()
        with self.assertRaises(models.dbGaPWorkspace.DoesNotExist):
            dar.get_dbgap_workspace()

    def test_get_dbgap_workspace_one_match(self):
        """Returns the correct workspace when there is one match."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_study_accession=workspace.dbgap_study_accession,
            dbgap_version=workspace.dbgap_version,
            dbgap_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        self.assertEqual(dar.get_dbgap_workspace(), workspace)

    def test_get_dbgap_workspace_different_version(self):
        """Raises ObjectNotFound for workspace with the same phs but different version."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_version=1)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_study_accession=workspace.dbgap_study_accession,
            dbgap_version=2,
            dbgap_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        with self.assertRaises(models.dbGaPWorkspace.DoesNotExist):
            dar.get_dbgap_workspace()

    def test_get_dbgap_workspace_different_participant_set(self):
        """Raises ObjectNotFound for workspace with the same phs/version but different participant set."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_participant_set=1)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_study_accession=workspace.dbgap_study_accession,
            dbgap_version=workspace.dbgap_version,
            dbgap_participant_set=2,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        with self.assertRaises(models.dbGaPWorkspace.DoesNotExist):
            dar.get_dbgap_workspace()

    def test_get_dbgap_workspace_different_dbgap_study_accession(self):
        """Raises ObjectNotFound for workspace with the same phs/version but different phs."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_study_accession__phs=1)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_study_accession__phs=2,
            dbgap_version=workspace.dbgap_version,
            dbgap_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        with self.assertRaises(models.dbGaPWorkspace.DoesNotExist):
            dar.get_dbgap_workspace()

    def test_get_dbgap_workspace_different_consent_code(self):
        """Raises ObjectNotFound for workspace with the same phs/version/participant set but different consent code."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_consent_code=1)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_study_accession=workspace.dbgap_study_accession,
            dbgap_version=workspace.dbgap_version,
            dbgap_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=2,
        )
        with self.assertRaises(models.dbGaPWorkspace.DoesNotExist):
            dar.get_dbgap_workspace()
