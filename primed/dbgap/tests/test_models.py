"""Tests of models in the `dbgap` app."""

from datetime import timedelta

import jsonschema
import responses
from anvil_consortium_manager.tests.factories import (
    GroupGroupMembershipFactory,
    ManagedGroupFactory,
    WorkspaceFactory,
    WorkspaceGroupAccessFactory,
)
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone
from faker import Faker

from primed.primed_anvil.tests.factories import DataUsePermissionFactory, StudyFactory
from primed.users.tests.factories import UserFactory

from .. import constants, models
from . import factories

fake = Faker()


class dbGaPStudyAccessionTest(TestCase):
    """Tests for the dbGaPStudyAccession model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        study = StudyFactory.create()
        instance = models.dbGaPStudyAccession(
            study=study,
            dbgap_phs=1,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPStudyAccession)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPStudyAccessionFactory.create(
            study__short_name="FOO",
            dbgap_phs=1,
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
            dbgap_phs=obj.dbgap_phs,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_phs", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_phs"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["dbgap_phs"][0].messages[0]
        )
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_study_protect(self):
        """Cannot delete a Study if it has an associated dbGaPWorkspace."""
        study = StudyFactory.create()
        factories.dbGaPStudyAccessionFactory.create(study=study)
        with self.assertRaises(ProtectedError):
            study.delete()

    def test_dbgap_phs_cannot_be_zero(self):
        """dbgap_phs cannot be zero."""
        study = StudyFactory.create()
        instance = factories.dbGaPStudyAccessionFactory.build(
            study=study,
            dbgap_phs=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_phs", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_phs"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_phs"][0].messages[0],
        )

    def test_dbgap_phs_cannot_be_negative(self):
        """dbgap_phs cannot be negative."""
        study = StudyFactory.create()
        instance = factories.dbGaPStudyAccessionFactory.build(
            study=study,
            dbgap_phs=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_phs", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_phs"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_phs"][0].messages[0],
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
            dbgap_study_accession__dbgap_phs=1,
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
            dbgap_study_accession__dbgap_phs=1, dbgap_version=2, dbgap_participant_set=3
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
            dbgap_project_id=1,
            anvil_group=anvil_group,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPApplication)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPApplicationFactory.create(
            dbgap_project_id=1,
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
            dbgap_project_id=obj.dbgap_project_id,
            anvil_group=anvil_group,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_project_id", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_project_id"]), 1)
        self.assertIn(
            "already exists", e.exception.error_dict["dbgap_project_id"][0].messages[0]
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
            dbgap_project_id=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_project_id", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_project_id"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_project_id"][0].messages[0],
        )

    def test_dbgap_phs_cannot_be_negative(self):
        """dbgap_phs cannot be negative."""
        pi = UserFactory.create()
        instance = factories.dbGaPApplicationFactory.build(
            principal_investigator=pi,
            dbgap_project_id=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_project_id", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_project_id"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_project_id"][0].messages[0],
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
            "Project_id": dbgap_application.dbgap_project_id,
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
            dbgap_application__dbgap_project_id=6512,
            dbgap_dar_data=valid_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            status=302,
            headers={
                "Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"
            },
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 1)
        new_object = dars[0]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 23497)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 421)
        self.assertEqual(new_object.original_version, 32)
        self.assertEqual(new_object.original_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 2)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 1)

    @responses.activate
    def test_dbgap_create_dars_from_json_one_study_two_dars(self):
        """Can create two DARs for one study."""
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
            dbgap_application__dbgap_project_id=6512,
            dbgap_dar_data=valid_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            status=302,
            headers={
                "Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"
            },
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 2)
        new_object = dars[0]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 23497)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 421)
        self.assertEqual(new_object.original_version, 32)
        self.assertEqual(new_object.original_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        new_object = dars[1]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertIn(new_object, dars)
        self.assertEqual(new_object.dbgap_dar_id, 23498)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 421)
        self.assertEqual(new_object.original_version, 32)
        self.assertEqual(new_object.original_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 2)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "NPU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 2)

    @responses.activate
    def test_dbgap_create_dars_from_json_two_studies_one_dar(self):
        """Can create one DAR for two studies."""
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
            dbgap_application__dbgap_project_id=6512,
            dbgap_dar_data=valid_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": "phs000421"})],
            status=302,
            headers={
                "Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"
            },
        )
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": "phs000896"})],
            status=302,
            headers={
                "Location": constants.DBGAP_STUDY_URL + "?study_id=phs000896.v2.p1"
            },
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 2)
        new_object = dars[0]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 23497)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 421)
        self.assertEqual(new_object.original_version, 32)
        self.assertEqual(new_object.original_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        new_object = dars[1]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertIn(new_object, dars)
        self.assertEqual(new_object.dbgap_dar_id, 23498)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 896)
        self.assertEqual(new_object.original_version, 2)
        self.assertEqual(new_object.original_participant_set, 1)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "DS-LD")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 2)

    @responses.activate
    def test_dbgap_create_dars_from_json_invalid_json(self):
        """JSON is validated."""
        invalid_json = {
            "Project_id": 6512,
            "PI_name": "Test Investigator",
            "Project_closed": "no",
        }
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__dbgap_project_id=6512,
            dbgap_dar_data=invalid_json,
        )
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            dbgap_snapshot.create_dars_from_json()
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    @responses.activate
    def test_dbgap_create_dars_from_json_mismatched_project_id(self):
        """No dbGaPDataAccessRequests are created if project_id doesn't match."""
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
            dbgap_application__dbgap_project_id=6512,
            dbgap_dar_data=valid_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            status=302,
            headers={
                "Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"
            },
        )
        with self.assertRaises(ValueError) as e:
            dbgap_snapshot.create_dars_from_json()
        self.assertIn("project_id does not match", str(e.exception))
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    @responses.activate
    def test_does_include_dars_that_are_not_approved(self):
        """Does creates DARs with a different status than approved."""
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
            dbgap_application__dbgap_project_id=6512,
            dbgap_dar_data=valid_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            status=302,
            headers={
                "Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"
            },
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 2)
        new_object = dars[0]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 23497)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 421)
        self.assertEqual(new_object.original_version, 32)
        self.assertEqual(new_object.original_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_object.dbgap_current_status, "rejected")
        new_object = dars[1]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 23498)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 421)
        self.assertEqual(new_object.original_version, 32)
        self.assertEqual(new_object.original_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 2)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "NPU")
        self.assertEqual(new_object.dbgap_current_status, "approved")

    @responses.activate
    def test_dbgap_create_dars_updated_dars(self):
        """Can create updated DARs and keep original version and participant set."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        valid_json = {
            "Project_id": dbgap_application.dbgap_project_id,
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
                            "current_DAR_status": "new",
                            "was_approved": "no",
                        },
                    ],
                },
            ],
        }
        original_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=valid_json,
            created=timezone.now() - timedelta(weeks=4),
        )
        # Create the original DAR.
        original_dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=original_snapshot,
            dbgap_dar_id=valid_json["studies"][0]["requests"][0]["DAR"],
            dbgap_phs=421,
            dbgap_consent_code=valid_json["studies"][0]["requests"][0]["consent_code"],
            dbgap_consent_abbreviation=valid_json["studies"][0]["requests"][0][
                "consent_abbrev"
            ],
            dbgap_current_status=valid_json["studies"][0]["requests"][0][
                "current_DAR_status"
            ],  # Make sure the current status is different.
            original_version=32,
            original_participant_set=18,
        )
        # Now create a new snapshot and DARs from that.
        # Update the current status.
        valid_json["studies"][0]["requests"][0]["current_DAR_status"] = "approved"
        valid_json["studies"][0]["requests"][0]["was_approved"] = "yes"
        second_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=valid_json,
            created=timezone.now(),
        )
        updated_dars = second_snapshot.create_dars_from_json()
        self.assertEqual(len(updated_dars), 1)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 2)
        updated_dar = updated_dars[0]
        self.assertIsInstance(updated_dar, models.dbGaPDataAccessRequest)
        self.assertNotEqual(updated_dar.pk, original_dar.pk)
        self.assertEqual(updated_dar.dbgap_dar_id, 23497)
        self.assertEqual(updated_dar.dbgap_data_access_snapshot, second_snapshot)
        self.assertEqual(updated_dar.dbgap_phs, 421)
        self.assertEqual(updated_dar.dbgap_consent_code, 2)
        self.assertEqual(updated_dar.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(updated_dar.dbgap_current_status, "approved")
        # These should be pulled from the original dar.
        self.assertEqual(updated_dar.original_version, original_dar.original_version)
        self.assertEqual(
            updated_dar.original_participant_set, original_dar.original_participant_set
        )

    @responses.activate
    def test_create_dars_from_json_one_update_one_new(self):
        """Can create updated DARs and keep original version and participant set."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        valid_json = {
            "Project_id": dbgap_application.dbgap_project_id,
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
                    ],
                },
            ],
        }
        original_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=valid_json,
            created=timezone.now() - timedelta(weeks=4),
        )
        # Create the original DAR.
        original_dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=original_snapshot,
            dbgap_dar_id=valid_json["studies"][0]["requests"][0]["DAR"],
            dbgap_phs=421,
            dbgap_consent_code=valid_json["studies"][0]["requests"][0]["consent_code"],
            dbgap_consent_abbreviation=valid_json["studies"][0]["requests"][0][
                "consent_abbrev"
            ],
            dbgap_current_status=valid_json["studies"][0]["requests"][0][
                "current_DAR_status"
            ],  # Make sure the current status is different.
            original_version=32,
            original_participant_set=18,
        )
        # Now create a new snapshot and DARs from that.
        # Add a new request to the JSON.
        valid_json["studies"][0]["requests"].append(
            {
                "DAC_abbrev": "FOOBI",
                "consent_abbrev": "NPU",
                "consent_code": 2,
                "DAR": 23498,
                "current_version": 12,
                "current_DAR_status": "approved",
                "was_approved": "yes",
            }
        )
        # The study version/participant set has been updated - add a response.
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            status=302,
            headers={
                "Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v33.p19"
            },
        )
        # Create the new snapshot.
        second_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=valid_json,
            created=timezone.now(),
        )
        new_dars = second_snapshot.create_dars_from_json()
        self.assertEqual(len(new_dars), 2)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 3)
        updated_dar = models.dbGaPDataAccessRequest.objects.filter(
            dbgap_dar_id=23497
        ).latest("pk")
        self.assertNotEqual(updated_dar.pk, original_dar.pk)
        self.assertEqual(updated_dar.dbgap_dar_id, 23497)
        self.assertEqual(updated_dar.dbgap_data_access_snapshot, second_snapshot)
        self.assertEqual(updated_dar.dbgap_phs, 421)
        self.assertEqual(updated_dar.dbgap_consent_code, 1)
        self.assertEqual(updated_dar.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(updated_dar.dbgap_current_status, "approved")
        # These should be pulled from the original dar.
        self.assertEqual(updated_dar.original_version, original_dar.original_version)
        self.assertEqual(
            updated_dar.original_participant_set, original_dar.original_participant_set
        )
        new_dar = models.dbGaPDataAccessRequest.objects.filter(
            dbgap_dar_id=23498
        ).latest("pk")
        self.assertIsInstance(new_dar, models.dbGaPDataAccessRequest)
        self.assertEqual(new_dar.dbgap_dar_id, 23498)
        self.assertEqual(new_dar.dbgap_data_access_snapshot, second_snapshot)
        self.assertEqual(new_dar.dbgap_phs, 421)
        self.assertEqual(new_dar.dbgap_consent_code, 2)
        self.assertEqual(new_dar.dbgap_consent_abbreviation, "NPU")
        self.assertEqual(new_dar.dbgap_current_status, "approved")
        # These should be pulled from the original dar.
        self.assertEqual(new_dar.original_version, 33)
        self.assertEqual(new_dar.original_participant_set, 19)

    @responses.activate
    def test_created_dars_from_json_assertion_error_phs(self):
        """Test that an AssertionError is raised when phs in updated json is unexpected for DAR ID."""
        """Can create updated DARs and keep original version and participant set."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        valid_json = {
            "Project_id": dbgap_application.dbgap_project_id,
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
        original_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=valid_json,
            created=timezone.now() - timedelta(weeks=4),
        )
        # Create the original DAR.
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=original_snapshot,
            dbgap_dar_id=valid_json["studies"][0]["requests"][0]["DAR"],
            dbgap_phs=421,
            dbgap_consent_code=valid_json["studies"][0]["requests"][0]["consent_code"],
            dbgap_consent_abbreviation=valid_json["studies"][0]["requests"][0][
                "consent_abbrev"
            ],
            dbgap_current_status=valid_json["studies"][0]["requests"][0][
                "current_DAR_status"
            ],  # Make sure the current status is different.
            original_version=32,
            original_participant_set=18,
        )
        # Now create a new snapshot and DARs from that.
        # Change the phs
        valid_json["studies"][0]["study_accession"] = "phs000892"
        second_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=valid_json,
            created=timezone.now(),
        )
        with self.assertRaises(ValueError) as e:
            second_snapshot.create_dars_from_json()
        self.assertIn("dbgap_phs", str(e.exception))
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 1)

    @responses.activate
    def test_created_dars_from_json_assertion_error_consent_code(self):
        """Test that an AssertionError is raised when consent_code in updated json is unexpected for DAR ID."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        valid_json = {
            "Project_id": dbgap_application.dbgap_project_id,
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
                    ],
                },
            ],
        }
        original_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=valid_json,
            created=timezone.now() - timedelta(weeks=4),
        )
        # Create the original DAR.
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=original_snapshot,
            dbgap_dar_id=valid_json["studies"][0]["requests"][0]["DAR"],
            dbgap_phs=421,
            dbgap_consent_code=valid_json["studies"][0]["requests"][0]["consent_code"],
            dbgap_consent_abbreviation=valid_json["studies"][0]["requests"][0][
                "consent_abbrev"
            ],
            dbgap_current_status=valid_json["studies"][0]["requests"][0][
                "current_DAR_status"
            ],  # Make sure the current status is different.
            original_version=32,
            original_participant_set=18,
        )
        # Now create a new snapshot and DARs from that.
        # Change the phs
        valid_json["studies"][0]["requests"][0]["consent_code"] = 2
        second_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=valid_json,
            created=timezone.now(),
        )
        with self.assertRaises(ValueError) as e:
            second_snapshot.create_dars_from_json()
        self.assertIn("dbgap_consent_code", str(e.exception))
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 1)

    @responses.activate
    def test_created_dars_from_json_assertion_error_dbgap_project_id(self):
        """Test that an AssertionError is raised when dbgap_project_id in updated json is unexpected for DAR ID."""
        dbgap_application = factories.dbGaPApplicationFactory.create(dbgap_project_id=2)
        valid_json = {
            "Project_id": dbgap_application.dbgap_project_id,
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
                    ],
                },
            ],
        }
        # Create an original DAR with a different project id. This shouldn't happen but...
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot__dbgap_application__dbgap_project_id=1,
            dbgap_dar_id=valid_json["studies"][0]["requests"][0]["DAR"],
            dbgap_phs=421,
            dbgap_consent_code=valid_json["studies"][0]["requests"][0]["consent_code"],
            dbgap_consent_abbreviation=valid_json["studies"][0]["requests"][0][
                "consent_abbrev"
            ],
            dbgap_current_status=valid_json["studies"][0]["requests"][0][
                "current_DAR_status"
            ],  # Make sure the current status is different.
            original_version=32,
            original_participant_set=18,
        )
        # Now create a new snapshot and DARs from that.
        # Change the phs
        second_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=valid_json,
            created=timezone.now(),
        )
        with self.assertRaises(ValueError) as e:
            second_snapshot.create_dars_from_json()
        self.assertIn("project_id", str(e.exception))
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 1)


class dbGaPDataAccessRequestTest(TestCase):
    """Tests for the dbGaPDataAccessRequest model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        instance = models.dbGaPDataAccessRequest(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_phs=1,
            dbgap_dar_id=1,
            original_version=2,
            original_participant_set=3,
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

    def test_unique_dbgap_dar_id(self):
        """Saving a duplicate model fails."""
        obj = factories.dbGaPDataAccessRequestFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=obj.dbgap_data_access_snapshot,
            dbgap_phs=fake.random_int(),
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

    def test_unique_dbgap_data_access_request(self):
        """Violating the unique_dbgap_data_access_request constraint fails."""
        obj = factories.dbGaPDataAccessRequestFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=obj.dbgap_data_access_snapshot,
            dbgap_phs=obj.dbgap_phs,
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
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=obj.dbgap_data_access_snapshot,
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
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=dbgap_snapshot
        )
        dbgap_snapshot.delete()
        with self.assertRaises(models.dbGaPDataAccessSnapshot.DoesNotExist):
            dbgap_snapshot.refresh_from_db()
        with self.assertRaises(models.dbGaPDataAccessRequest.DoesNotExist):
            dar.refresh_from_db()

    def test_dbgap_dar_id_cannot_be_zero(self):
        """dbgap_dar_id cannot be zero."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
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
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
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

    def test_dbgap_phs_cannot_be_zero(self):
        """dbgap_phs cannot be zero."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_phs=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_phs", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_phs"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_phs"][0].messages[0],
        )

    def test_dbgap_phs_cannot_be_negative(self):
        """dbgap_phs cannot be negative."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            dbgap_phs=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_phs", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_phs"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["dbgap_phs"][0].messages[0],
        )

    def test_original_version_cannot_be_zero(self):
        """original_version cannot be zero."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            original_version=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("original_version", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["original_version"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["original_version"][0].messages[0],
        )

    def test_original_version_cannot_be_negative(self):
        """original_version cannot be negative."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            original_version=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("original_version", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["original_version"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["original_version"][0].messages[0],
        )

    def test_original_participant_set_cannot_be_zero(self):
        """original_participant_set cannot be zero."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            original_participant_set=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("original_participant_set", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["original_participant_set"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["original_participant_set"][0].messages[0],
        )

    def test_original_participant_set_cannot_be_negative(self):
        """original_participant_set cannot be negative."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
            original_participant_set=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("original_participant_set", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["original_participant_set"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["original_participant_set"][0].messages[0],
        )

    def test_dbgap_consent_code_cannot_be_zero(self):
        """consent_code cannot be zero."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
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
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_data_access_snapshot=dbgap_snapshot,
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

    def test_get_dbgap_workspace_no_study_accession(self):
        """Raises DoesNotExist when there is no matching study accession."""
        dar = factories.dbGaPDataAccessRequestFactory.create()
        with self.assertRaises(models.dbGaPStudyAccession.DoesNotExist):
            dar.get_dbgap_workspace()

    def test_get_dbgap_workspace_no_matches(self):
        """Raises DoesNotExist when there is no matching workspace."""
        study_accession = factories.dbGaPStudyAccessionFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=study_accession.dbgap_phs
        )
        with self.assertRaises(models.dbGaPWorkspace.DoesNotExist):
            dar.get_dbgap_workspace()

    def test_get_dbgap_workspace_one_match(self):
        """Returns the correct workspace when there is one match."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=workspace.dbgap_version,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        self.assertEqual(dar.get_dbgap_workspace(), workspace)

    def test_get_dbgap_workspace_different_version(self):
        """Raises ObjectNotFound for workspace with the same phs but different version."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_version=1)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=2,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        with self.assertRaises(models.dbGaPWorkspace.DoesNotExist):
            dar.get_dbgap_workspace()

    def test_get_dbgap_workspace_different_participant_set(self):
        """Raises ObjectNotFound for workspace with the same phs/version but different participant set."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_participant_set=1)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=workspace.dbgap_version,
            original_participant_set=2,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        with self.assertRaises(models.dbGaPWorkspace.DoesNotExist):
            dar.get_dbgap_workspace()

    def test_get_dbgap_workspace_different_dbgap_study_accession(self):
        """Raises ObjectNotFound for workspace with the same phs/version but different phs."""
        workspace = factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession__dbgap_phs=1
        )
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=2,
            original_version=workspace.dbgap_version,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        with self.assertRaises(models.dbGaPStudyAccession.DoesNotExist):
            dar.get_dbgap_workspace()

    def test_get_dbgap_workspace_different_consent_code(self):
        """Raises ObjectNotFound for workspace with the same phs/version/participant set but different consent code."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_consent_code=1)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=workspace.dbgap_version,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=2,
        )
        with self.assertRaises(models.dbGaPWorkspace.DoesNotExist):
            dar.get_dbgap_workspace()

    def test_has_access_no_match_no_study_accession(self):
        """has_access raises exception when no matching workspace exists."""
        data_access_request = factories.dbGaPDataAccessRequestFactory.create()
        with self.assertRaises(models.dbGaPStudyAccession.DoesNotExist):
            data_access_request.has_access()

    def test_has_access_no_match(self):
        """has_access raises exception when no matching workspace exists."""
        data_access_request = factories.dbGaPDataAccessRequestFactory.create()
        factories.dbGaPStudyAccessionFactory.create(
            dbgap_phs=data_access_request.dbgap_phs
        )
        with self.assertRaises(models.dbGaPWorkspace.DoesNotExist):
            data_access_request.has_access()

    def test_has_access_match_no_access(self):
        """has_access returns False when the managed group does not have access to the workspace for this DAR."""
        data_access_request = factories.dbGaPDataAccessRequestFactory.create()
        factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession__dbgap_phs=data_access_request.dbgap_phs,
            dbgap_version=data_access_request.original_version,
            dbgap_participant_set=data_access_request.original_participant_set,
            dbgap_consent_code=data_access_request.dbgap_consent_code,
        )
        self.assertFalse(data_access_request.has_access())

    def test_has_access_match_access(self):
        """has_access returns True when the managed group has access to the workspace for this DAR."""
        data_access_request = factories.dbGaPDataAccessRequestFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession__dbgap_phs=data_access_request.dbgap_phs,
            dbgap_version=data_access_request.original_version,
            dbgap_participant_set=data_access_request.original_participant_set,
            dbgap_consent_code=data_access_request.dbgap_consent_code,
        )
        WorkspaceGroupAccessFactory.create(
            workspace=dbgap_workspace.workspace,
            group=data_access_request.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        self.assertTrue(data_access_request.has_access())

    def test_has_access_shared_in_auth_domain(self):
        """Returns True if the workspace is shared and the group is in the auth domain."""
        # Create a workspace with an auth domain.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        # Create a DAR.
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=dbgap_workspace.dbgap_study_accession.dbgap_phs,
            original_version=dbgap_workspace.dbgap_version,
            original_participant_set=dbgap_workspace.dbgap_participant_set,
            dbgap_consent_code=dbgap_workspace.dbgap_consent_code,
        )
        # Share the workspace with the group.
        WorkspaceGroupAccessFactory.create(
            workspace=dbgap_workspace.workspace,
            group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        # Add the group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=auth_domain,
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        self.assertTrue(dar.has_access())

    def test_has_access_shared_not_in_auth_domain(self):
        """Returns False if the workspace is shared but the group is not in the auth domain."""
        # Create a workspace with an auth domain.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        # Create a DAR.
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=dbgap_workspace.dbgap_study_accession.dbgap_phs,
            original_version=dbgap_workspace.dbgap_version,
            original_participant_set=dbgap_workspace.dbgap_participant_set,
            dbgap_consent_code=dbgap_workspace.dbgap_consent_code,
        )
        # Share the workspace with the group.
        WorkspaceGroupAccessFactory.create(
            workspace=dbgap_workspace.workspace,
            group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        # Do not add the group to the auth domain.
        self.assertFalse(dar.has_access())

    def test_has_access_in_auth_domain_not_shared(self):
        """Returns False if the workspace is not shared but the group is in the auth domain."""
        # Create a workspace with an auth domain.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        # Create a DAR.
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=dbgap_workspace.dbgap_study_accession.dbgap_phs,
            original_version=dbgap_workspace.dbgap_version,
            original_participant_set=dbgap_workspace.dbgap_participant_set,
            dbgap_consent_code=dbgap_workspace.dbgap_consent_code,
        )
        # Do not share the workspace with the group.
        # Add the group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=auth_domain,
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        self.assertFalse(dar.has_access())

    def test_has_access_shared_in_auth_domain_indirectly(self):
        """Returns True if the workspace is shared and the group is indirectly in the auth domain."""
        # Create a workspace with an auth domain.
        auth_domain = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain)
        # Create a DAR.
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=dbgap_workspace.dbgap_study_accession.dbgap_phs,
            original_version=dbgap_workspace.dbgap_version,
            original_participant_set=dbgap_workspace.dbgap_participant_set,
            dbgap_consent_code=dbgap_workspace.dbgap_consent_code,
        )
        # Share the workspace with the group.
        WorkspaceGroupAccessFactory.create(
            workspace=dbgap_workspace.workspace,
            group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        # Create a parent group
        parent_group = ManagedGroupFactory.create()
        # Add the group to the parent group.
        GroupGroupMembershipFactory.create(
            parent_group=parent_group,
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        # Add the parent group to the auth domain.
        GroupGroupMembershipFactory.create(
            parent_group=auth_domain, child_group=parent_group
        )
        self.assertTrue(dar.has_access())

    def test_has_access_shared_two_auth_domains(self):
        """Returns True if the workspace is shared and the group is in both auth domains."""
        # Create a workspace with an auth domain.
        auth_domain_1 = ManagedGroupFactory.create()
        auth_domain_2 = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain_1)
        dbgap_workspace.workspace.authorization_domains.add(auth_domain_2)
        # Create a DAR.
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=dbgap_workspace.dbgap_study_accession.dbgap_phs,
            original_version=dbgap_workspace.dbgap_version,
            original_participant_set=dbgap_workspace.dbgap_participant_set,
            dbgap_consent_code=dbgap_workspace.dbgap_consent_code,
        )
        # Share the workspace with the group.
        WorkspaceGroupAccessFactory.create(
            workspace=dbgap_workspace.workspace,
            group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        # Add the group to the auth domains.
        GroupGroupMembershipFactory.create(
            parent_group=auth_domain_1,
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        GroupGroupMembershipFactory.create(
            parent_group=auth_domain_2,
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        self.assertTrue(dar.has_access())

    def test_has_access_shared_two_auth_domains_only_in_one(self):
        """Returns False if the workspace is shared and the group is in only one of the two auth domains."""
        # Create a workspace with an auth domain.
        auth_domain_1 = ManagedGroupFactory.create()
        auth_domain_2 = ManagedGroupFactory.create()
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_workspace.workspace.authorization_domains.add(auth_domain_1)
        dbgap_workspace.workspace.authorization_domains.add(auth_domain_2)
        # Create a DAR.
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=dbgap_workspace.dbgap_study_accession.dbgap_phs,
            original_version=dbgap_workspace.dbgap_version,
            original_participant_set=dbgap_workspace.dbgap_participant_set,
            dbgap_consent_code=dbgap_workspace.dbgap_consent_code,
        )
        # Share the workspace with the group.
        WorkspaceGroupAccessFactory.create(
            workspace=dbgap_workspace.workspace,
            group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        # Add the group to only one of the auth domains.
        GroupGroupMembershipFactory.create(
            parent_group=auth_domain_2,
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        self.assertFalse(dar.has_access())

    def test_has_access_indirectly_shared(self):
        """Returns True if the workspace is indirectly shared with the dbGaP group."""
        # Create a workspace and matching DAR.
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=dbgap_workspace.dbgap_study_accession.dbgap_phs,
            original_version=dbgap_workspace.dbgap_version,
            original_participant_set=dbgap_workspace.dbgap_participant_set,
            dbgap_consent_code=dbgap_workspace.dbgap_consent_code,
        )
        # Create a parent group
        parent_group = ManagedGroupFactory.create()
        # Share the workspace with the parent group.
        WorkspaceGroupAccessFactory.create(
            workspace=dbgap_workspace.workspace,
            group=parent_group,
        )
        # Add the group to the parent group.
        GroupGroupMembershipFactory.create(
            parent_group=parent_group,
            child_group=dar.dbgap_data_access_snapshot.dbgap_application.anvil_group,
        )
        self.assertTrue(dar.has_access())
