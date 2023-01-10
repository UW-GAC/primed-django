import random

from anvil_consortium_manager.adapters.workspace import workspace_adapter_registry
from anvil_consortium_manager.tests.factories import WorkspaceFactory
from factory import Faker, SubFactory, lazy_attribute
from factory.django import DjangoModelFactory

from primed.users.tests.factories import UserFactory

from .. import adapters, models


class SimulatedDataWorkspaceFactory(DjangoModelFactory):
    """A factory for the SimulatedDataWorkspace model."""

    workspace = SubFactory(WorkspaceFactory, workspace_type="simulated_data")
    requested_by = SubFactory(UserFactory)

    class Meta:
        model = models.SimulatedDataWorkspace


class ConsortiumDevelWorkspaceFactory(DjangoModelFactory):
    """A factory for the ConsortiumDevelWorkspace model."""

    workspace = SubFactory(
        WorkspaceFactory,
        workspace_type=adapters.ConsortiumDevelWorkspaceAdapter().get_type(),
    )
    requested_by = SubFactory(UserFactory)

    class Meta:
        model = models.ConsortiumDevelWorkspace


class ExampleWorkspaceFactory(DjangoModelFactory):
    """A factory for the ExampleWorkspace model."""

    workspace = SubFactory(
        WorkspaceFactory,
        workspace_type=adapters.ExampleWorkspaceAdapter().get_type(),
    )
    requested_by = SubFactory(UserFactory)

    class Meta:
        model = models.ExampleWorkspace


class TemplateWorkspaceFactory(DjangoModelFactory):
    """A factory for the TemplateWorkspace model."""

    workspace = SubFactory(
        WorkspaceFactory,
        workspace_type=adapters.TemplateWorkspaceAdapter().get_type(),
    )

    class Meta:
        model = models.TemplateWorkspace

    @lazy_attribute
    def intended_workspace_type(self):
        """Select a random registered workspace_type other than template."""
        registered_types = list(
            workspace_adapter_registry.get_registered_adapters().keys()
        )
        registered_types.remove(adapters.TemplateWorkspaceAdapter().get_type())
        return random.choice(registered_types)


class OpenAccessWorkspaceFactory(DjangoModelFactory):
    """A factory for the OpenAccessWorkspace model."""

    workspace = SubFactory(WorkspaceFactory, workspace_type="open_access")
    requested_by = SubFactory(UserFactory)
    data_source = Faker("paragraph")

    class Meta:
        model = models.OpenAccessWorkspace
