"""Tests of models in the `dbgap` app."""

from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import TestCase

from primed.primed_anvil.tests.factories import DataUsePermissionFactory, StudyFactory
from primed.users.tests.factories import UserFactory

from .. import models
from . import factories


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
            dbgap_consent_abbreviation="GRU-NPU",
            data_use_permission=data_use_permission,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPWorkspace)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession__study__short_name="TEST",
            dbgap_study_accession__phs=1,
            dbgap_version=2,
            dbgap_participant_set=3,
            dbgap_consent_abbreviation="GRU-NPU",
        )
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "TEST (phs000001.v2.p3 - GRU-NPU)")

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
        instance = models.dbGaPApplication(
            principal_investigator=pi,
            project_id=1,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPApplication)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        pi = UserFactory.create()
        instance = factories.dbGaPApplicationFactory.create(
            principal_investigator=pi,
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
        instance = factories.dbGaPApplicationFactory.build(
            principal_investigator=pi,
            project_id=obj.project_id,
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


class dbGaPDataAccessRequestTest(TestCase):
    """Tests for the dbGaPDataAccessRequest model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = models.dbGaPDataAccessRequest(
            dbgap_application=dbgap_application,
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
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_application=dbgap_application,
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

    def test_dbgap_application_protect(self):
        """Cannot delete a dbGaPApplication if it has an associated dbGaPDataAccessRequest."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_application=dbgap_application
        )
        with self.assertRaises(ProtectedError):
            dbgap_application.delete()

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
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_application=dbgap_application,
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
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_application=dbgap_application,
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
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_application=dbgap_application,
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
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_application=dbgap_application,
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
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_application=dbgap_application,
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
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_application=dbgap_application,
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
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_application=dbgap_application,
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
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = factories.dbGaPDataAccessRequestFactory.build(
            dbgap_application=dbgap_application,
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
