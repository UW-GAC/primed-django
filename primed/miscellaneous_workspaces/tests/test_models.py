""" "Model tests for the `miscellaneous_workspaces` app."""

from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.core.exceptions import ValidationError
from django.test import TestCase

from primed.primed_anvil.tests.factories import AvailableDataFactory, StudyFactory
from primed.users.tests.factories import UserFactory

from .. import models
from . import factories


class SimulatedDataWorkspaceTest(TestCase):
    """Tests for the SimulatedDataWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        instance = models.SimulatedDataWorkspace(workspace=workspace, requested_by=user)
        instance.save()
        self.assertIsInstance(instance, models.SimulatedDataWorkspace)

    def test_str_method(self):
        workspace = WorkspaceFactory.create(billing_project__name="test-bp", name="test-ws")
        instance = factories.SimulatedDataWorkspaceFactory.create(workspace=workspace)
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), "test-bp/test-ws")


class ConsortiumDevelWorkspaceTest(TestCase):
    """Tests for the ConsortiumDevelWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        instance = models.ConsortiumDevelWorkspace(workspace=workspace, requested_by=user)
        instance.save()
        self.assertIsInstance(instance, models.ConsortiumDevelWorkspace)

    def test_str_method(self):
        workspace = WorkspaceFactory.create(billing_project__name="test-bp", name="test-ws")
        instance = factories.ConsortiumDevelWorkspaceFactory.create(workspace=workspace)
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), "test-bp/test-ws")


class ResourceWorkspaceTest(TestCase):
    """Tests for the ResourceWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        instance = models.ResourceWorkspace(workspace=workspace, requested_by=user)
        instance.save()
        self.assertIsInstance(instance, models.ResourceWorkspace)

    def test_str_method(self):
        workspace = WorkspaceFactory.create(billing_project__name="test-bp", name="test-ws")
        instance = factories.ResourceWorkspaceFactory.create(workspace=workspace)
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), "test-bp/test-ws")


class TemplateWorkspaceTest(TestCase):
    """Tests for the TemplateWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        instance = models.TemplateWorkspace(workspace=workspace, intended_usage="Test")
        instance.save()
        self.assertIsInstance(instance, models.TemplateWorkspace)

    def test_str_method(self):
        workspace = WorkspaceFactory.create(billing_project__name="test-bp", name="test-ws")
        instance = factories.TemplateWorkspaceFactory.create(workspace=workspace)
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), "test-bp/test-ws")


class OpenAccessWorkspaceTest(TestCase):
    """Tests for the OpenAccessWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        instance = models.OpenAccessWorkspace(workspace=workspace, requested_by=user)
        instance.save()
        self.assertIsInstance(instance, models.OpenAccessWorkspace)

    def test_str_method(self):
        workspace = WorkspaceFactory.create(billing_project__name="test-bp", name="test-ws")
        instance = factories.OpenAccessWorkspaceFactory.create(workspace=workspace)
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), "test-bp/test-ws")

    def test_one_study(self):
        instance = factories.OpenAccessWorkspaceFactory.create()
        study = StudyFactory.create()
        instance.studies.add(study)
        self.assertEqual(instance.studies.count(), 1)
        self.assertIn(study, instance.studies.all())

    def test_two_studies(self):
        instance = factories.OpenAccessWorkspaceFactory.create()
        studies = StudyFactory.create_batch(2)
        instance.studies.add(*studies)
        self.assertEqual(instance.studies.count(), 2)
        self.assertIn(studies[0], instance.studies.all())
        self.assertIn(studies[1], instance.studies.all())

    def test_one_available_data(self):
        instance = factories.OpenAccessWorkspaceFactory.create()
        available_data = AvailableDataFactory.create()
        instance.available_data.add(available_data)
        self.assertEqual(instance.available_data.count(), 1)
        self.assertIn(available_data, instance.available_data.all())

    def test_two_available_data(self):
        instance = factories.OpenAccessWorkspaceFactory.create()
        available_data = AvailableDataFactory.create_batch(2)
        instance.available_data.add(*available_data)
        self.assertEqual(instance.available_data.count(), 2)
        self.assertIn(available_data[0], instance.available_data.all())
        self.assertIn(available_data[1], instance.available_data.all())

    def test_data_url(self):
        workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        instance = models.OpenAccessWorkspace(workspace=workspace, requested_by=user, data_url="http://www.example.com")
        self.assertEqual(instance.data_url, "http://www.example.com")


class DataPrepWorkspaceTest(TestCase):
    """Tests for the DataPrepWorkspace model."""

    def test_model_saving(self):
        """Creation using the model constructor and .save() works."""
        workspace = WorkspaceFactory.create()
        target_workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        instance = models.DataPrepWorkspace(workspace=workspace, target_workspace=target_workspace, requested_by=user)
        instance.save()
        self.assertIsInstance(instance, models.DataPrepWorkspace)

    def test_str_method(self):
        workspace = WorkspaceFactory.create(billing_project__name="test-bp", name="test-ws")
        instance = factories.DataPrepWorkspaceFactory.create(workspace=workspace)
        self.assertIsInstance(str(instance), str)
        self.assertEqual(str(instance), "test-bp/test-ws")

    def test_two_update_workspaces_for_same_final_workspace(self):
        target_workspace = WorkspaceFactory.create()
        instance_1 = factories.DataPrepWorkspaceFactory.create(target_workspace=target_workspace)
        instance_2 = factories.DataPrepWorkspaceFactory.create(target_workspace=target_workspace)
        self.assertEqual(target_workspace.data_prep_workspaces.count(), 2)
        self.assertIn(instance_1, target_workspace.data_prep_workspaces.all())
        self.assertIn(instance_2, target_workspace.data_prep_workspaces.all())

    def test_clean_original_workspace_different_than_workspace(self):
        """Clean method raises ValidationError when workspace is the same as original_workspace."""
        workspace = WorkspaceFactory.create()
        user = UserFactory.create()
        instance = models.DataPrepWorkspace(requested_by=user, workspace=workspace, target_workspace=workspace)
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("target_workspace", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["target_workspace"]), 1)
        self.assertIn(
            "target_workspace must be different",
            e.exception.message_dict["target_workspace"][0],
        )

    def test_clean_target_workspace_cannot_be_a_data_prep_workspace(self):
        """Clean method raises ValidationError when the original_workspace is a data prep workspace."""
        workspace = WorkspaceFactory.create()
        target_workspace = factories.DataPrepWorkspaceFactory.create()
        user = UserFactory.create()
        instance = models.DataPrepWorkspace(
            requested_by=user,
            workspace=workspace,
            target_workspace=target_workspace.workspace,
        )
        with self.assertRaises(ValidationError) as e:
            instance.full_clean()
        self.assertEqual(len(e.exception.message_dict), 1)
        self.assertIn("target_workspace", e.exception.message_dict)
        self.assertEqual(len(e.exception.message_dict["target_workspace"]), 1)
        self.assertIn(
            "cannot be a DataPrepWorkspace",
            e.exception.message_dict["target_workspace"][0],
        )
