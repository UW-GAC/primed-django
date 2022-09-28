"""Tests of models in the `dbgap` app."""

from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import TestCase

from primed.primed_anvil.tests.factories import DataUsePermissionFactory, StudyFactory

from .. import models
from . import factories


class dbGaPWorkspaceTest(TestCase):
    """Tests for the dbGaPWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        study = StudyFactory.create()
        data_use_permission = DataUsePermissionFactory.create()
        instance = models.dbGaPWorkspace(
            workspace=workspace,
            # study_consent_group=study_consent_group,
            study=study,
            data_use_permission=data_use_permission,
            data_use_limitations="test limitations",
            full_consent_code="GRU-NPU",
            phs=1,
            version=1,
            participant_set=1,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPWorkspace)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPWorkspaceFactory.create(
            phs=1,
            version=2,
            participant_set=3,
            full_consent_code="GRU-NPU",
        )
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "phs000001.v2.p3 - GRU-NPU")

    def test_unique_dbgap_workspace(self):
        """Saving a duplicate model fails."""
        study = StudyFactory.create()
        factories.dbGaPWorkspaceFactory.create(study=study, phs=1, version=1)
        data_use_permission = DataUsePermissionFactory.create()
        workspace = WorkspaceFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            study=study,
            phs=1,
            version=1,
            workspace=workspace,
            data_use_permission=data_use_permission,
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

    def test_study_protect(self):
        """Cannot delete a Study if it has an associated dbGaPWorkspace."""
        study = StudyFactory.create()
        factories.dbGaPWorkspaceFactory.create(study=study)
        with self.assertRaises(ProtectedError):
            study.delete()

    def test_phs_cannot_be_zero(self):
        """phs cannot be zero."""
        study = StudyFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
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
        instance = factories.dbGaPWorkspaceFactory.build(
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

    def test_version_cannot_be_zero(self):
        """version cannot be zero."""
        study = StudyFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            study=study,
            version=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("version", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["version"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["version"][0].messages[0],
        )

    def test_version_cannot_be_negative(self):
        """version cannot be negative."""
        study = StudyFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            study=study,
            version=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("version", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["version"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["version"][0].messages[0],
        )

    def test_participant_set_cannot_be_zero(self):
        """participant_set cannot be zero."""
        study = StudyFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            study=study,
            participant_set=0,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("participant_set", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["participant_set"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["participant_set"][0].messages[0],
        )

    def test_participant_set_cannot_be_negative(self):
        """participant_set cannot be negative."""
        study = StudyFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            study=study,
            participant_set=-1,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("participant_set", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["participant_set"]), 1)
        self.assertIn(
            "greater than or equal to 1",
            e.exception.error_dict["participant_set"][0].messages[0],
        )

    def test_get_dbgap_accession(self):
        """`get_dbgap_accession` returns the correct string"""
        instance = factories.dbGaPWorkspaceFactory.create(
            phs=1, version=2, participant_set=3
        )
        self.assertEqual(instance.get_dbgap_accession(), "phs000001.v2.p3")
