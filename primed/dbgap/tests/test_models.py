"""Tests of models in the `dbgap` app."""

from datetime import timedelta

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
from django.utils import timezone
from faker import Faker

from primed.duo.tests.factories import DataUseModifierFactory, DataUsePermissionFactory
from primed.primed_anvil.tests.factories import AvailableDataFactory, StudyFactory
from primed.users.tests.factories import UserFactory

from .. import constants, models
from . import factories

fake = Faker()


class dbGaPStudyAccessionTest(TestCase):
    """Tests for the dbGaPStudyAccession model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        instance = models.dbGaPStudyAccession(
            dbgap_phs=1,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPStudyAccession)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPStudyAccessionFactory.create(
            dbgap_phs=1,
        )
        instance.save()
        self.assertIsInstance(instance.__str__(), str)
        self.assertEqual(instance.__str__(), "phs000001")

    def test_get_absolute_url(self):
        """get_absolute_url method works correctly."""
        instance = factories.dbGaPStudyAccessionFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)

    def test_unique_dbgap_study_accession(self):
        """Saving a duplicate model fails."""
        obj = factories.dbGaPStudyAccessionFactory.create()
        #        study = StudyFactory.create()
        instance = factories.dbGaPStudyAccessionFactory.build(
            #            study=study,
            dbgap_phs=obj.dbgap_phs,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_phs", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_phs"]), 1)
        self.assertIn("already exists", e.exception.error_dict["dbgap_phs"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_dbgap_phs_cannot_be_zero(self):
        """dbgap_phs cannot be zero."""
        instance = factories.dbGaPStudyAccessionFactory.build(
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
        instance = factories.dbGaPStudyAccessionFactory.build(
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

    def test_one_study(self):
        study = StudyFactory.create()
        instance = models.dbGaPStudyAccession(dbgap_phs=1)
        instance.save()
        instance.studies.add(study)
        self.assertEqual(instance.studies.count(), 1)
        self.assertIn(study, instance.studies.all())

    def test_two_studies(self):
        study_1 = StudyFactory.create()
        study_2 = StudyFactory.create()
        instance = models.dbGaPStudyAccession(dbgap_phs=1)
        instance.save()
        instance.studies.add(study_1)
        instance.studies.add(study_2)
        self.assertEqual(instance.studies.count(), 2)
        self.assertIn(study_1, instance.studies.all())
        self.assertIn(study_2, instance.studies.all())


class dbGaPWorkspaceTest(TestCase):
    """Tests for the dbGaPWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        user = UserFactory.create()
        workspace = WorkspaceFactory.create()
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        instance = models.dbGaPWorkspace(
            workspace=workspace,
            dbgap_study_accession=dbgap_study_accession,
            dbgap_version=1,
            dbgap_participant_set=1,
            data_use_limitations="test limitations",
            dbgap_consent_code=1,
            dbgap_consent_abbreviation="GRU-NPU",
            acknowledgments="test acknowledgments",
            requested_by=user,
            gsr_restricted=False,
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

    def test_can_add_data_use_permission(self):
        """Saving a model with data_use_permission set is valid."""
        data_use_permission = DataUsePermissionFactory.create()
        instance = factories.dbGaPWorkspaceFactory.create(
            data_use_permission=data_use_permission,
        )
        self.assertIsInstance(instance, models.dbGaPWorkspace)
        self.assertEqual(instance.data_use_permission, data_use_permission)

    def test_can_add_data_use_modifiers(self):
        """Saving a model with data_use_permission and data_use_modifiers set is valid."""
        data_use_modifiers = DataUseModifierFactory.create_batch(2)
        instance = factories.dbGaPWorkspaceFactory.create()
        instance.data_use_modifiers.add(*data_use_modifiers)
        self.assertIsInstance(instance, models.dbGaPWorkspace)
        self.assertIn(data_use_modifiers[0], instance.data_use_modifiers.all())
        self.assertIn(data_use_modifiers[1], instance.data_use_modifiers.all())

    def test_unique_dbgap_workspace(self):
        """Saving a duplicate model fails."""
        dbgap_workspace = factories.dbGaPWorkspaceFactory.create()
        workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        instance = factories.dbGaPWorkspaceFactory.build(
            dbgap_study_accession=dbgap_workspace.dbgap_study_accession,
            dbgap_version=dbgap_workspace.dbgap_version,
            dbgap_consent_abbreviation=dbgap_workspace.dbgap_consent_abbreviation,
            # These are here to prevent ValueErrors about unsaved related objects.
            workspace=workspace,
            requested_by=user,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("__all__", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["__all__"]), 1)
        self.assertIn("already exists", e.exception.error_dict["__all__"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_dbgap_study_accession_protect(self):
        """Cannot delete a dbGaPStudyAccession if it has an associated dbGaPWorkspace."""
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create()
        factories.dbGaPWorkspaceFactory.create(dbgap_study_accession=dbgap_study_accession)
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

    def test_get_data_access_requests_no_dars(self):
        """Returns no results when there no DARs."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        self.assertEqual(len(workspace.get_data_access_requests()), 0)

    def test_get_data_access_requests_different_phs(self):
        """Does not return a DAR where participant set doesn't match."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs + 1,
            original_version=workspace.dbgap_version,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        self.assertEqual(len(workspace.get_data_access_requests()), 0)

    def test_get_data_access_requests_larger_version(self):
        """Does not return a DAR that has a later version than this workspace."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=workspace.dbgap_version + 1,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        self.assertEqual(len(workspace.get_data_access_requests()), 0)

    def test_get_data_access_requests_smaller_version(self):
        """Does return a DAR that has an earlier version than this workspace."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_version=2)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=1,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        results = workspace.get_data_access_requests()
        self.assertEqual(len(results), 1)
        self.assertIn(dar, results)

    def test_get_data_access_requests_larger_participant_set(self):
        """Does not return a DAR where participant set is larger than the workspace."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=workspace.dbgap_version,
            original_participant_set=workspace.dbgap_participant_set + 1,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        self.assertEqual(len(workspace.get_data_access_requests()), 0)

    def test_get_data_access_requests_smaller_participant_set(self):
        """Does return a DAR where participant set is smaller than the workspace."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_version=2, dbgap_participant_set=2)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=1,
            original_participant_set=1,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        results = workspace.get_data_access_requests()
        self.assertEqual(len(results), 1)
        self.assertIn(dar, results)

    def test_get_data_access_requests_different_consent_code(self):
        """Does not return a DAR where consent code doesn't match."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=workspace.dbgap_version,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code + 1,
        )
        self.assertEqual(len(workspace.get_data_access_requests()), 0)

    def test_get_data_access_requests_one_application_one_snapshot_one_match(self):
        """Returns 1 results when there is one matching DARs."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestForWorkspaceFactory(dbgap_workspace=workspace)
        results = workspace.get_data_access_requests()
        self.assertEqual(len(results), 1)
        self.assertIn(dar, results)

    def test_get_data_access_requests_one_application_two_snapshots_most_recent_false(
        self,
    ):
        """Returns 2 results when there are two matchign DARs from different snapshots of the same application."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_application = factories.dbGaPApplicationFactory.create()
        snapshot_1 = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=False,
        )
        snapshot_2 = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            created=timezone.now(),
            is_most_recent=True,
        )
        dar_1 = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace, dbgap_data_access_snapshot=snapshot_1
        )
        dar_2 = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace, dbgap_data_access_snapshot=snapshot_2
        )
        results = workspace.get_data_access_requests()
        self.assertEqual(len(results), 2)
        self.assertIn(dar_1, results)
        self.assertIn(dar_2, results)

    def test_get_data_access_requests_one_application_two_snapshots_most_recent_true(
        self,
    ):
        """Returns 1 results when there are two matchign DARs from different snapshots of the same application."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dbgap_application = factories.dbGaPApplicationFactory.create()
        snapshot_1 = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            created=timezone.now() - timedelta(weeks=4),
            is_most_recent=False,
        )
        snapshot_2 = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            created=timezone.now(),
            is_most_recent=True,
        )
        dar_1 = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace, dbgap_data_access_snapshot=snapshot_1
        )
        dar_2 = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace, dbgap_data_access_snapshot=snapshot_2
        )
        results = workspace.get_data_access_requests(most_recent=True)
        self.assertEqual(len(results), 1)
        self.assertNotIn(dar_1, results)
        self.assertIn(dar_2, results)

    def test_get_data_access_requests_two_applications_with_match(self):
        """Returns 2 results when there are two matchign DARs from different applications."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        application_1 = factories.dbGaPApplicationFactory.create()
        application_2 = factories.dbGaPApplicationFactory.create()
        dar_1 = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace,
            dbgap_data_access_snapshot__dbgap_application=application_1,
        )
        dar_2 = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace,
            dbgap_data_access_snapshot__dbgap_application=application_2,
        )
        results = workspace.get_data_access_requests()
        self.assertEqual(len(results), 2)
        self.assertIn(dar_1, results)
        self.assertIn(dar_2, results)

    def test_get_data_access_requests_all_statuses(self):
        """Returns 1 results when there is one matching DARs."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar_approved = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED,
        )
        dar_closed = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED,
        )
        dar_rejected = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED,
        )
        dar_expired = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.EXPIRED,
        )
        dar_new = factories.dbGaPDataAccessRequestForWorkspaceFactory(
            dbgap_workspace=workspace,
            dbgap_current_status=models.dbGaPDataAccessRequest.NEW,
        )
        results = workspace.get_data_access_requests()
        self.assertEqual(len(results), 5)
        self.assertIn(dar_approved, results)
        self.assertIn(dar_closed, results)
        self.assertIn(dar_rejected, results)
        self.assertIn(dar_expired, results)
        self.assertIn(dar_new, results)

    def test_available_data(self):
        """Can add available data to a workspace."""
        available_data = AvailableDataFactory.create_batch(2)
        instance = factories.dbGaPWorkspaceFactory.create()
        instance.save()
        instance.available_data.add(*available_data)
        self.assertIsInstance(instance, models.dbGaPWorkspace)
        self.assertIn(available_data[0], instance.available_data.all())
        self.assertIn(available_data[1], instance.available_data.all())

    def test_get_dbgap_link(self):
        workspace = factories.dbGaPWorkspaceFactory.create()
        self.assertIsInstance(workspace.get_dbgap_link(), str)


class dbGaPApplicationTest(TestCase):
    """Tests for the dbGaPApplication model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        pi = UserFactory.create()
        anvil_access_group = ManagedGroupFactory.create()
        instance = models.dbGaPApplication(
            principal_investigator=pi,
            dbgap_project_id=1,
            anvil_access_group=anvil_access_group,
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
        anvil_access_group = ManagedGroupFactory.create()
        instance = factories.dbGaPApplicationFactory.build(
            principal_investigator=pi,
            dbgap_project_id=obj.dbgap_project_id,
            anvil_access_group=anvil_access_group,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertIn("dbgap_project_id", e.exception.error_dict)
        self.assertEqual(len(e.exception.error_dict["dbgap_project_id"]), 1)
        self.assertIn("already exists", e.exception.error_dict["dbgap_project_id"][0].messages[0])
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

    def test_can_add_collaborators(self):
        """Saving a model with collaborators set is valid."""
        collaborators = UserFactory.create_batch(2)
        instance = factories.dbGaPApplicationFactory.create()
        instance.collaborators.add(*collaborators)
        self.assertIn(collaborators[0], instance.collaborators.all())
        self.assertIn(collaborators[1], instance.collaborators.all())


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
            is_most_recent=True,
        )
        instance.save()
        self.assertIsInstance(instance, models.dbGaPDataAccessSnapshot)

    def test_str_method(self):
        """The custom __str__ method returns the correct string."""
        instance = factories.dbGaPDataAccessSnapshotFactory.create()
        self.assertIsInstance(instance.__str__(), str)

    def test_get_absolute_url(self):
        """get_absolute_url method works correctly."""
        instance = factories.dbGaPDataAccessSnapshotFactory.create()
        self.assertIsInstance(instance.get_absolute_url(), str)

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
            is_most_recent=True,
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
        factories.dbGaPDataAccessSnapshotFactory.create(dbgap_application=dbgap_application)
        with self.assertRaises(ProtectedError):
            dbgap_application.delete()

    @responses.activate
    def test_dbgap_create_dars_from_json_one_study_one_dar(self):
        """Can create one DAR for one study."""
        dar_json = factories.dbGaPJSONRequestFactory(
            DAC_abbrev="FOO",
            consent_abbrev="GRU",
            consent_code=1,
            DAR=1234,
            current_DAR_status="approved",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession="phs000421", requests=[dar_json])
        project_json = factories.dbGaPJSONProjectFactory(studies=[study_json])
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__dbgap_project_id=project_json["Project_id"],
            dbgap_dar_data=project_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"},
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 1)
        new_object = dars[0]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 1234)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 421)
        self.assertEqual(new_object.original_version, 32)
        self.assertEqual(new_object.original_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        self.assertEqual(new_object.dbgap_dac, "FOO")
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 1)

    @responses.activate
    def test_dbgap_create_dars_from_json_one_study_two_dars(self):
        """Can create two DARs for one study."""
        dar_json_1 = factories.dbGaPJSONRequestFactory(
            DAC_abbrev="FOO",
            consent_abbrev="GRU",
            consent_code=1,
            DAR=1234,
            current_DAR_status="approved",
        )
        dar_json_2 = factories.dbGaPJSONRequestFactory(
            DAC_abbrev="FOO",
            consent_abbrev="NPU",
            consent_code=2,
            DAR=1235,
            current_DAR_status="approved",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession="phs000421", requests=[dar_json_1, dar_json_2])
        project_json = factories.dbGaPJSONProjectFactory(studies=[study_json])
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__dbgap_project_id=project_json["Project_id"],
            dbgap_dar_data=project_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"},
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 2)
        new_object = dars[0]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 1234)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 421)
        self.assertEqual(new_object.original_version, 32)
        self.assertEqual(new_object.original_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        self.assertEqual(new_object.dbgap_dac, "FOO")
        new_object = dars[1]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertIn(new_object, dars)
        self.assertEqual(new_object.dbgap_dar_id, 1235)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 421)
        self.assertEqual(new_object.original_version, 32)
        self.assertEqual(new_object.original_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 2)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "NPU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        self.assertEqual(new_object.dbgap_dac, "FOO")
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 2)

    @responses.activate
    def test_dbgap_create_dars_from_json_two_studies_one_dar_each(self):
        """Can create one DAR for two studies."""
        dar_json_1 = factories.dbGaPJSONRequestFactory(
            DAC_abbrev="FOO",
            consent_abbrev="GRU",
            consent_code=1,
            DAR=1234,
            current_DAR_status="approved",
        )
        dar_json_2 = factories.dbGaPJSONRequestFactory(
            DAC_abbrev="BAR",
            consent_abbrev="NPU",
            consent_code=2,
            DAR=1235,
            current_DAR_status="approved",
        )
        study_json_1 = factories.dbGaPJSONStudyFactory(study_accession="phs000421", requests=[dar_json_1])
        study_json_2 = factories.dbGaPJSONStudyFactory(study_accession="phs000896", requests=[dar_json_2])
        project_json = factories.dbGaPJSONProjectFactory(studies=[study_json_1, study_json_2])

        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__dbgap_project_id=project_json["Project_id"],
            dbgap_dar_data=project_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": "phs000421"})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"},
        )
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            match=[responses.matchers.query_param_matcher({"study_id": "phs000896"})],
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=phs000896.v2.p1"},
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 2)
        new_object = dars[0]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertEqual(new_object.dbgap_dar_id, 1234)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 421)
        self.assertEqual(new_object.original_version, 32)
        self.assertEqual(new_object.original_participant_set, 18)
        self.assertEqual(new_object.dbgap_consent_code, 1)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "GRU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        self.assertEqual(new_object.dbgap_dac, "FOO")
        new_object = dars[1]
        self.assertIsInstance(new_object, models.dbGaPDataAccessRequest)
        self.assertIn(new_object, dars)
        self.assertEqual(new_object.dbgap_dar_id, 1235)
        self.assertEqual(new_object.dbgap_data_access_snapshot, dbgap_snapshot)
        self.assertEqual(new_object.dbgap_phs, 896)
        self.assertEqual(new_object.original_version, 2)
        self.assertEqual(new_object.original_participant_set, 1)
        self.assertEqual(new_object.dbgap_consent_code, 2)
        self.assertEqual(new_object.dbgap_consent_abbreviation, "NPU")
        self.assertEqual(new_object.dbgap_current_status, "approved")
        self.assertEqual(new_object.dbgap_dac, "BAR")
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 2)

    @responses.activate
    def test_dbgap_create_dars_from_json_invalid_json(self):
        """JSON is validated."""
        project_json = factories.dbGaPJSONProjectFactory()
        project_json.pop("studies")
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__dbgap_project_id=project_json["Project_id"],
            dbgap_dar_data=project_json,
        )
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            dbgap_snapshot.create_dars_from_json()
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    @responses.activate
    def test_dbgap_create_dars_from_json_mismatched_project_id(self):
        """No dbGaPDataAccessRequests are created if project_id doesn't match."""
        project_json = factories.dbGaPJSONProjectFactory(Project_id=1)
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__dbgap_project_id=2,
            dbgap_dar_data=project_json,
        )
        with self.assertRaises(ValueError) as e:
            dbgap_snapshot.create_dars_from_json()
        self.assertIn("project_id does not match", str(e.exception))
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 0)

    @responses.activate
    def test_does_include_dars_that_are_not_approved(self):
        """Does creates DARs with a different status than approved."""
        dar_json = factories.dbGaPJSONRequestFactory(
            DAC_abbrev="FOO",
            consent_abbrev="GRU",
            consent_code=1,
            DAR=1234,
            current_DAR_status="rejected",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession="phs000421", requests=[dar_json])
        project_json = factories.dbGaPJSONProjectFactory(studies=[study_json])
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application__dbgap_project_id=project_json["Project_id"],
            dbgap_dar_data=project_json,
        )
        # Add responses with the study version and participant_set.
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v32.p18"},
        )
        dars = dbgap_snapshot.create_dars_from_json()
        self.assertEqual(len(dars), 1)
        new_object = dars[0]
        self.assertEqual(new_object.dbgap_current_status, "rejected")
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 1)

    @responses.activate
    def test_dbgap_create_dars_updated_dars(self):
        """Can create updated DARs and keep original version and participant set."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dar_json = factories.dbGaPJSONRequestFactory(
            DAC_abbrev="FOO",
            consent_abbrev="GRU",
            consent_code=1,
            DAR=1234,
            current_DAR_status="approved",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession="phs000421", requests=[dar_json])
        project_json = factories.dbGaPJSONProjectFactory(
            Project_id=dbgap_application.dbgap_project_id, studies=[study_json]
        )
        original_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
        )
        # Create the original DAR.
        original_dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=original_snapshot,
            dbgap_dar_id=dar_json["DAR"],
            dbgap_phs=421,
            dbgap_consent_code=dar_json["consent_code"],
            dbgap_consent_abbreviation=dar_json["consent_abbrev"],
            dbgap_current_status="approved",
            original_version=32,
            original_participant_set=18,
        )
        # Now create a new snapshot and DARs from that.
        second_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now(),
        )
        updated_dars = second_snapshot.create_dars_from_json()
        self.assertEqual(len(updated_dars), 1)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 2)
        updated_dar = updated_dars[0]
        self.assertIsInstance(updated_dar, models.dbGaPDataAccessRequest)
        self.assertNotEqual(updated_dar.pk, original_dar.pk)
        self.assertEqual(updated_dar.dbgap_data_access_snapshot, second_snapshot)
        # These should be pulled from the original dar.
        self.assertEqual(updated_dar.original_version, original_dar.original_version)
        self.assertEqual(updated_dar.original_participant_set, original_dar.original_participant_set)

    @responses.activate
    def test_dbgap_create_dars_version_change_between_new_and_approved(self):
        """Sets version and participant set to the current version for an DAR that went from new to approved."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dar_json = factories.dbGaPJSONRequestFactory(
            DAC_abbrev="FOO",
            consent_abbrev="GRU",
            consent_code=1,
            DAR=1234,
            current_DAR_status="approved",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession="phs000421", requests=[dar_json])
        project_json = factories.dbGaPJSONProjectFactory(
            Project_id=dbgap_application.dbgap_project_id, studies=[study_json]
        )

        original_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
        )
        # Create the original DAR.
        original_dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=original_snapshot,
            dbgap_dar_id=dar_json["DAR"],
            dbgap_phs=421,
            dbgap_consent_code=dar_json["consent_code"],
            dbgap_consent_abbreviation=dar_json["consent_abbrev"],
            dbgap_current_status="new",  # Make sure the current status is not approved.
            original_version=32,
            original_participant_set=18,
        )
        # Now create a new snapshot and DARs from that.
        second_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now(),
        )
        # Add responses with a new study version and participant_set.
        responses.add(
            responses.GET,
            constants.DBGAP_STUDY_URL,
            status=302,
            headers={"Location": constants.DBGAP_STUDY_URL + "?study_id=phs000421.v33.p19"},
        )
        updated_dars = second_snapshot.create_dars_from_json()
        self.assertEqual(len(updated_dars), 1)
        self.assertEqual(models.dbGaPDataAccessRequest.objects.count(), 2)
        updated_dar = updated_dars[0]
        self.assertIsInstance(updated_dar, models.dbGaPDataAccessRequest)
        self.assertNotEqual(updated_dar.pk, original_dar.pk)
        self.assertEqual(updated_dar.dbgap_data_access_snapshot, second_snapshot)
        # These should be pulled from the original dar.
        self.assertEqual(updated_dar.original_version, 33)
        self.assertEqual(updated_dar.original_participant_set, 19)

    @responses.activate
    def test_created_dars_from_json_assertion_error_phs(self):
        """Test that an AssertionError is raised when phs in updated json is unexpected for DAR ID."""
        dbgap_application = factories.dbGaPApplicationFactory.create()
        dar_json = factories.dbGaPJSONRequestFactory(
            DAC_abbrev="FOO",
            consent_abbrev="GRU",
            consent_code=1,
            DAR=1234,
            current_DAR_status="approved",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession="phs000892", requests=[dar_json])
        project_json = factories.dbGaPJSONProjectFactory(
            Project_id=dbgap_application.dbgap_project_id, studies=[study_json]
        )
        original_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
        )
        # Create the original DAR.
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=original_snapshot,
            dbgap_dar_id=dar_json["DAR"],
            dbgap_phs=421,
            dbgap_consent_code=dar_json["consent_code"],
            dbgap_consent_abbreviation=dar_json["consent_abbrev"],
            original_version=32,
            original_participant_set=18,
        )
        # Now create a new snapshot and DARs from that.
        # Change the phs.
        second_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
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
        dar_json = factories.dbGaPJSONRequestFactory(
            DAC_abbrev="FOO",
            consent_abbrev="GRU",
            consent_code=2,
            DAR=1234,
            current_DAR_status="approved",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession="phs000421", requests=[dar_json])
        project_json = factories.dbGaPJSONProjectFactory(
            Project_id=dbgap_application.dbgap_project_id, studies=[study_json]
        )
        original_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
        )
        # Create the original DAR.
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot=original_snapshot,
            dbgap_dar_id=dar_json["DAR"],
            dbgap_phs=421,
            dbgap_consent_code=1,
            dbgap_consent_abbreviation=dar_json["consent_abbrev"],
            dbgap_current_status=dar_json["current_DAR_status"],
            original_version=32,
            original_participant_set=18,
        )
        # Now create a new snapshot and DARs from that, with a different consent code..
        second_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
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
        dar_json = factories.dbGaPJSONRequestFactory(
            DAC_abbrev="FOO",
            consent_abbrev="GRU",
            consent_code=1,
            DAR=1234,
            current_DAR_status="approved",
        )
        study_json = factories.dbGaPJSONStudyFactory(study_accession="phs000421", requests=[dar_json])
        project_json = factories.dbGaPJSONProjectFactory(
            Project_id=dbgap_application.dbgap_project_id, studies=[study_json]
        )
        factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
            created=timezone.now() - timedelta(weeks=4),
        )
        # Create an original DAR with a different project id. This shouldn't happen but...
        factories.dbGaPDataAccessRequestFactory.create(
            dbgap_data_access_snapshot__dbgap_application__dbgap_project_id=1,
            dbgap_dar_id=1234,
            dbgap_phs=421,
            dbgap_current_status="approved",
            dbgap_consent_code=1,
            dbgap_consent_abbreviation="GRU",
        )
        # Now create a new snapshot and DARs from that, with the mismatched project id.
        second_snapshot = factories.dbGaPDataAccessSnapshotFactory.create(
            dbgap_application=dbgap_application,
            dbgap_dar_data=project_json,
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
            dbgap_dac="TEST",
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
        self.assertIn("already exists", e.exception.error_dict["__all__"][0].messages[0])
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
        self.assertIn("already exists", e.exception.error_dict["__all__"][0].messages[0])
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
        self.assertIn("already exists", e.exception.error_dict["__all__"][0].messages[0])
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_dbgap_data_access_snapshot_protect(self):
        """Cannot delete a dbGaPApplication if it has an associated dbGaPDataAccessSnapshot."""
        dbgap_snapshot = factories.dbGaPDataAccessSnapshotFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create(dbgap_data_access_snapshot=dbgap_snapshot)
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
        new_dar = factories.dbGaPDataAccessRequestFactory.create(dbgap_current_status=models.dbGaPDataAccessRequest.NEW)
        qs = models.dbGaPDataAccessRequest.objects.approved()
        self.assertEqual(len(qs), 1)
        self.assertIn(approved_dar, qs)
        self.assertNotIn(closed_dar, qs)
        self.assertNotIn(rejected_dar, qs)
        self.assertNotIn(expired_dar, qs)
        self.assertNotIn(new_dar, qs)

    def test_is_approved(self):
        """The is_approved property works correctly."""
        self.assertTrue(
            factories.dbGaPDataAccessRequestFactory.create(
                dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED
            ).is_approved
        )
        self.assertFalse(
            factories.dbGaPDataAccessRequestFactory.create(
                dbgap_current_status=models.dbGaPDataAccessRequest.CLOSED
            ).is_approved
        )
        self.assertFalse(
            factories.dbGaPDataAccessRequestFactory.create(
                dbgap_current_status=models.dbGaPDataAccessRequest.REJECTED
            ).is_approved
        )
        self.assertFalse(
            factories.dbGaPDataAccessRequestFactory.create(
                dbgap_current_status=models.dbGaPDataAccessRequest.EXPIRED
            ).is_approved
        )
        self.assertFalse(
            factories.dbGaPDataAccessRequestFactory.create(
                dbgap_current_status=models.dbGaPDataAccessRequest.NEW
            ).is_approved
        )

    def test_get_dbgap_workspaces_no_study_accession(self):
        """Raises DoesNotExist when there is no matching study accession."""
        dar = factories.dbGaPDataAccessRequestFactory.create()
        with self.assertRaises(models.dbGaPStudyAccession.DoesNotExist):
            dar.get_dbgap_workspaces()

    def test_get_dbgap_workspaces_no_matches(self):
        """Returns an empty queryset when there is no matching workspace."""
        study_accession = factories.dbGaPStudyAccessionFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create(dbgap_phs=study_accession.dbgap_phs)
        self.assertEqual(dar.get_dbgap_workspaces().count(), 0)

    def test_get_dbgap_workspaces_one_match(self):
        """Returns the correct workspace when there is one match."""
        workspace = factories.dbGaPWorkspaceFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=workspace.dbgap_version,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        qs = dar.get_dbgap_workspaces()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0], workspace)

    def test_get_dbgap_workspaces_two_matches(self):
        """Returns the correct workspace when there are two match."""
        study_accession = factories.dbGaPStudyAccessionFactory.create()
        workspace_1 = factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession=study_accession,
            dbgap_version=1,
            dbgap_participant_set=1,
            dbgap_consent_code=1,
        )
        workspace_2 = factories.dbGaPWorkspaceFactory.create(
            dbgap_study_accession=study_accession,
            dbgap_version=2,
            dbgap_participant_set=1,
            dbgap_consent_code=1,
        )

        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=study_accession.dbgap_phs,
            original_version=1,
            original_participant_set=1,
            dbgap_consent_code=1,
        )
        qs = dar.get_dbgap_workspaces()
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0], workspace_1)
        self.assertEqual(qs[1], workspace_2)

    def test_get_dbgap_workspaces_smaller_version(self):
        """Raises ObjectNotFound for workspace with the same phs but a smaller version."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_version=1)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=2,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        qs = dar.get_dbgap_workspaces()
        self.assertEqual(qs.count(), 0)

    def test_get_dbgap_workspaces_larger_version(self):
        """Finds match for workspace with the same phs but a larger version."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_version=3)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=2,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        qs = dar.get_dbgap_workspaces()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0], workspace)

    def test_get_dbgap_workspaces_smaller_participant_set(self):
        """Raises ObjectNotFound for workspace with the same phs/version but different participant set."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_participant_set=1)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=workspace.dbgap_version,
            original_participant_set=2,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        qs = dar.get_dbgap_workspaces()
        self.assertEqual(qs.count(), 0)

    def test_get_dbgap_workspaces_larger_participant_set(self):
        """Finds a matching workspace with a larger version and participant set."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_version=2, dbgap_participant_set=2)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=1,
            original_participant_set=1,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        qs = dar.get_dbgap_workspaces()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0], workspace)

    def test_get_dbgap_workspaces_different_dbgap_study_accession(self):
        """Raises ObjectNotFound for workspace with the same phs/version but different phs."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_study_accession__dbgap_phs=1)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=2,
            original_version=workspace.dbgap_version,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=workspace.dbgap_consent_code,
        )
        with self.assertRaises(models.dbGaPStudyAccession.DoesNotExist):
            dar.get_dbgap_workspaces()

    def test_get_dbgap_workspaces_different_consent_code(self):
        """Raises ObjectNotFound for workspace with the same phs/version/participant set but different consent code."""
        workspace = factories.dbGaPWorkspaceFactory.create(dbgap_consent_code=1)
        dar = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=workspace.dbgap_study_accession.dbgap_phs,
            original_version=workspace.dbgap_version,
            original_participant_set=workspace.dbgap_participant_set,
            dbgap_consent_code=2,
        )
        qs = dar.get_dbgap_workspaces()
        self.assertEqual(qs.count(), 0)

    def test_get_dbgap_accession(self):
        """`get_dbgap_accession` returns the correct string"""
        instance = factories.dbGaPDataAccessRequestFactory.create(
            dbgap_phs=1, original_version=2, original_participant_set=3
        )
        self.assertEqual(instance.get_dbgap_accession(), "phs000001.v2.p3")

    def test_get_dbgap_link(self):
        """`get_dbgab_link` returns a link."""
        instance = factories.dbGaPDataAccessRequestFactory.create()
        self.assertIsInstance(instance.get_dbgap_link(), str)

    def test_get_studies_no_matches(self):
        """Returns an empty queryset when there is no matching studies."""
        factories.dbGaPStudyAccessionFactory.create()
        dar = factories.dbGaPDataAccessRequestFactory.create()
        self.assertEqual(dar.get_matching_studies().count(), 0)

    def test_get_studies_one_match(self):
        """Returns the correct study when there is one match."""
        test_study = StudyFactory.create(short_name="Test", full_name="Test Study")
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create(dbgap_phs=1, studies=[test_study])
        dar = factories.dbGaPDataAccessRequestFactory.create(dbgap_phs=dbgap_study_accession.dbgap_phs)
        qs = dar.get_matching_studies()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0], test_study)

    def test_get_studies_two_match(self):
        """Returns the correct studies when there are 2 match."""
        test_study_1 = StudyFactory.create(short_name="Test 1", full_name="Test Study 1")
        test_study_2 = StudyFactory.create(short_name="Test 2", full_name="Test Study 2")
        dbgap_study_accession = factories.dbGaPStudyAccessionFactory.create(
            dbgap_phs=1, studies=[test_study_1, test_study_2]
        )
        dar = factories.dbGaPDataAccessRequestFactory.create(dbgap_phs=dbgap_study_accession.dbgap_phs)
        qs = dar.get_matching_studies()
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0], test_study_1)
        self.assertEqual(qs[1], test_study_2)
