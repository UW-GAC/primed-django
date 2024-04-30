"""Tests for migrations in the miscellaneous_workspaces app."""

from django_test_migrations.contrib.unittest_case import MigratorTestCase


class ExampleToResourceWorkspaceForwardMigrationTest(MigratorTestCase):
    """Tests for the migrations associated with renaming the ExampleWorkspace to ResourceWorkspace."""

    migrate_from = ("miscellaneous_workspaces", "0008_dataprepworkspace_historicaldataprepworkspace")
    migrate_to = ("miscellaneous_workspaces", "0010_update_workspace_type_field")

    def prepare(self):
        """Prepare some example workspaces to be migrated."""
        # Get model definition from the old state.
        BillingProject = self.old_state.apps.get_model("anvil_consortium_manager", "BillingProject")
        Workspace = self.old_state.apps.get_model("anvil_consortium_manager", "Workspace")
        ExampleWorkspace = self.old_state.apps.get_model("miscellaneous_workspaces", "ExampleWorkspace")
        User = self.old_state.apps.get_model("users", "User")
        # Create required fks.
        # requester = User.objects.create()
        billing_project = BillingProject.objects.create(name="bp", has_app_as_user=True)
        user = User.objects.create(name="Test User")
        # Create some example workspaces for testing.
        self.workspace_1 = Workspace.objects.create(
            billing_project=billing_project,
            name="example-workspace-1",
            workspace_type="example",
        )
        self.example_workspace_1 = ExampleWorkspace.objects.create(
            workspace=self.workspace_1,
            requested_by=user,
        )
        self.workspace_2 = Workspace.objects.create(
            billing_project=billing_project,
            name="example-workspace-2",
            workspace_type="example",
        )
        self.example_workspace_2 = ExampleWorkspace.objects.create(
            workspace=self.workspace_2,
            requested_by=user,
        )
        # Create a workspace with a different type.
        self.other_workspace = Workspace.objects.create(
            billing_project=billing_project,
            name="other-workspace",
            workspace_type="dbgap",
        )

    def test_workspace_updates(self):
        """Test updates to the workspace model."""
        Workspace = self.new_state.apps.get_model("anvil_consortium_manager", "Workspace")
        self.new_state.apps.get_model("miscellaneous_workspaces", "ResourceWorkspace")
        workspace = Workspace.objects.get(pk=self.workspace_1.pk)
        self.assertEqual(workspace.workspace_type, "resource")
        workspace.full_clean()
        workspace = Workspace.objects.get(pk=self.workspace_2.pk)
        self.assertEqual(workspace.workspace_type, "resource")
        workspace.full_clean()
        # Check the other workspace.
        other_workspace = Workspace.objects.get(pk=self.other_workspace.pk)
        self.assertEqual(other_workspace.workspace_type, "dbgap")

    def test_resource_workspace_updates(self):
        """Test updates to the ResourceWorkspace model."""
        ResourceWorkspace = self.new_state.apps.get_model("miscellaneous_workspaces", "ResourceWorkspace")
        resource_workspace = ResourceWorkspace.objects.get(pk=self.example_workspace_1.pk)
        resource_workspace.full_clean()
        resource_workspace = ResourceWorkspace.objects.get(pk=self.example_workspace_2.pk)
        resource_workspace.full_clean()

    def test_relationships(self):
        """relationships and reverse relationships are correct after migration."""
        Workspace = self.new_state.apps.get_model("anvil_consortium_manager", "Workspace")
        ResourceWorkspace = self.new_state.apps.get_model("miscellaneous_workspaces", "ResourceWorkspace")
        workspace = Workspace.objects.get(pk=self.workspace_1.pk)
        resource_workspace = ResourceWorkspace.objects.get(pk=self.example_workspace_1.pk)
        self.assertTrue(hasattr(workspace, "resourceworkspace"))
        self.assertIsInstance(workspace.resourceworkspace, ResourceWorkspace)
        self.assertEqual(workspace.resourceworkspace, resource_workspace)
        workspace = Workspace.objects.get(pk=self.workspace_2.pk)
        resource_workspace = ResourceWorkspace.objects.get(pk=self.example_workspace_2.pk)
        self.assertTrue(hasattr(workspace, "resourceworkspace"))
        self.assertIsInstance(workspace.resourceworkspace, ResourceWorkspace)
        self.assertEqual(workspace.resourceworkspace, resource_workspace)


class ExampleToResourceWorkspaceReverseMigrationTest(MigratorTestCase):
    """Tests for the reverse migrations associated with renaming the ExampleWorkspace to ResourceWorkspace."""

    migrate_from = ("miscellaneous_workspaces", "0010_update_workspace_type_field")
    migrate_to = ("miscellaneous_workspaces", "0008_dataprepworkspace_historicaldataprepworkspace")

    def prepare(self):
        """Prepare some example workspaces to be migrated."""
        # Get model definition from the old state.
        BillingProject = self.old_state.apps.get_model("anvil_consortium_manager", "BillingProject")
        Workspace = self.old_state.apps.get_model("anvil_consortium_manager", "Workspace")
        ResourceWorkspace = self.old_state.apps.get_model("miscellaneous_workspaces", "ResourceWorkspace")
        User = self.old_state.apps.get_model("users", "User")
        # Create required fks.
        # requester = User.objects.create()
        billing_project = BillingProject.objects.create(name="bp", has_app_as_user=True)
        user = User.objects.create(name="Test User")
        # Create some example workspaces for testing.
        self.workspace_1 = Workspace.objects.create(
            billing_project=billing_project,
            name="resource-workspace-1",
            workspace_type="resource",
        )
        self.resource_workspace_1 = ResourceWorkspace.objects.create(
            workspace=self.workspace_1,
            requested_by=user,
        )
        self.workspace_2 = Workspace.objects.create(
            billing_project=billing_project,
            name="resource-workspace-2",
            workspace_type="resource",
        )
        self.resource_workspace_2 = ResourceWorkspace.objects.create(
            workspace=self.workspace_2,
            requested_by=user,
        )
        # Create a workspace with a different type.
        self.other_workspace = Workspace.objects.create(
            billing_project=billing_project,
            name="other-workspace",
            workspace_type="dbgap",
        )

    def test_workspace_updates(self):
        """Test updates to the workspace model."""
        Workspace = self.new_state.apps.get_model("anvil_consortium_manager", "Workspace")
        workspace = Workspace.objects.get(pk=self.workspace_1.pk)
        self.assertEqual(workspace.workspace_type, "example")
        workspace.full_clean()
        workspace = Workspace.objects.get(pk=self.workspace_2.pk)
        self.assertEqual(workspace.workspace_type, "example")
        workspace.full_clean()
        # Check the other workspace.
        other_workspace = Workspace.objects.get(pk=self.other_workspace.pk)
        self.assertEqual(other_workspace.workspace_type, "dbgap")

    def test_resource_workspace_updates(self):
        """Test updates to the ResourceWorkspace model."""
        ExampleWorkspace = self.new_state.apps.get_model("miscellaneous_workspaces", "ExampleWorkspace")
        example_workspace = ExampleWorkspace.objects.get(pk=self.resource_workspace_1.pk)
        example_workspace.full_clean()
        example_workspace = ExampleWorkspace.objects.get(pk=self.resource_workspace_2.pk)
        example_workspace.full_clean()

    def test_relationships(self):
        """relationships and reverse relationships are correct after migration."""
        Workspace = self.new_state.apps.get_model("anvil_consortium_manager", "Workspace")
        ExampleWorkspace = self.new_state.apps.get_model("miscellaneous_workspaces", "ExampleWorkspace")
        workspace = Workspace.objects.get(pk=self.workspace_1.pk)
        example_workspace = ExampleWorkspace.objects.get(pk=self.resource_workspace_1.pk)
        self.assertTrue(hasattr(workspace, "exampleworkspace"))
        self.assertIsInstance(workspace.exampleworkspace, ExampleWorkspace)
        self.assertEqual(workspace.exampleworkspace, example_workspace)
        workspace = Workspace.objects.get(pk=self.workspace_2.pk)
        example_workspace = ExampleWorkspace.objects.get(pk=self.resource_workspace_2.pk)
        self.assertTrue(hasattr(workspace, "exampleworkspace"))
        self.assertIsInstance(workspace.exampleworkspace, ExampleWorkspace)
        self.assertEqual(workspace.exampleworkspace, example_workspace)
