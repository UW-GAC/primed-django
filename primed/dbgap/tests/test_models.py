"""Tests of models in the `dbgap` app."""

from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import TestCase

from primed.primed_anvil.tests.factories import DataUsePermissionFactory, StudyFactory

from .. import models
from . import factories


class dbGaPStudyTest(TestCase):
    """Tests for the dbGaPStudy model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        study = StudyFactory.create()
        instance = models.dbGaPStudy(
            study=study,
            phs=1,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPStudy)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPStudyFactory.create(
            study__short_name="FOO",
            phs=1,
        )
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "phs000001 - FOO")

    def test_get_absolute_url(self):
        """get_absolute_url method works correctly."""
        instance = factories.dbGaPStudyFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)

    def test_unique_dbgap_study(self):
        """Saving a duplicate model fails."""
        obj = factories.dbGaPStudyFactory.create()
        study = StudyFactory.create()
        instance = factories.dbGaPStudyFactory.build(
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
        factories.dbGaPStudyFactory.create(study=study)
        with self.assertRaises(ProtectedError):
            study.delete()

    def test_phs_cannot_be_zero(self):
        """phs cannot be zero."""
        study = StudyFactory.create()
        instance = factories.dbGaPStudyFactory.build(
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
        instance = factories.dbGaPStudyFactory.build(
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
        dbgap_study = factories.dbGaPStudyFactory.create()
        data_use_permission = DataUsePermissionFactory.create()
        instance = models.dbGaPWorkspace(
            workspace=workspace,
            dbgap_study=dbgap_study,
            dbgap_version=1,
            dbgap_participant_set=1,
            data_use_limitations="test limitations",
            full_consent_code="GRU-NPU",
            data_use_permission=data_use_permission,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPWorkspace)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPWorkspaceFactory.create(
            dbgap_study__study__short_name="TEST",
            dbgap_study__phs=1,
            dbgap_version=2,
            dbgap_participant_set=3,
            full_consent_code="GRU-NPU",
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
            dbgap_study=dbgap_workspace.dbgap_study,
            dbgap_version=dbgap_workspace.dbgap_version,
            full_consent_code=dbgap_workspace.full_consent_code,
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

    def test_dbgap_study_protect(self):
        """Cannot delete a dbGaPStudy if it has an associated dbGaPWorkspace."""
        dbgap_study = factories.dbGaPStudyFactory.create()
        factories.dbGaPWorkspaceFactory.create(dbgap_study=dbgap_study)
        with self.assertRaises(ProtectedError):
            dbgap_study.delete()

    def test_dbgap_version_cannot_be_zero(self):
        """dbgap_version cannot be zero."""
        dbgap_study = factories.dbGaPStudyFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study=dbgap_study,
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
        dbgap_study = factories.dbGaPStudyFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study=dbgap_study,
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
        dbgap_study = factories.dbGaPStudyFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study=dbgap_study,
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
        dbgap_study = factories.dbGaPStudyFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study=dbgap_study,
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
            dbgap_study__phs=1, dbgap_version=2, dbgap_participant_set=3
        )
        self.assertEqual(instance.get_dbgap_accession(), "phs000001.v2.p3")
