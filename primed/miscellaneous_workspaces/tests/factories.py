from anvil_consortium_manager.tests.factories import WorkspaceFactory
from factory import SubFactory
from factory.django import DjangoModelFactory

from .. import adapters, models


class SimulatedDataWorkspaceFactory(DjangoModelFactory):
    """A factory for the SimulatedDataWorkspace model."""

    workspace = SubFactory(WorkspaceFactory, workspace_type="simulated_data")

    class Meta:
        model = models.SimulatedDataWorkspace


class ConsortiumDevelWorkspaceFactory(DjangoModelFactory):
    """A factory for the ConsortiumDevelWorkspace model."""

    workspace = SubFactory(
        WorkspaceFactory,
        workspace_type=adapters.ConsortiumDevelWorkspaceAdapter().get_type(),
    )

    class Meta:
        model = models.ConsortiumDevelWorkspace


class ExampleWorkspaceFactory(DjangoModelFactory):
    """A factory for the ExampleWorkspace model."""

    workspace = SubFactory(
        WorkspaceFactory,
        workspace_type=adapters.ExampleWorkspaceAdapter().get_type(),
    )

    class Meta:
        model = models.ExampleWorkspace
