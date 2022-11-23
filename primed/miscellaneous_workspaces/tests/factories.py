from anvil_consortium_manager.tests.factories import WorkspaceFactory
from factory import SubFactory
from factory.django import DjangoModelFactory

from .. import models


class SimulatedDataWorkspaceFactory(DjangoModelFactory):
    """A factory for the SimulatedDataWorkspace model."""

    workspace = SubFactory(WorkspaceFactory, workspace_type="simulated_data")

    class Meta:
        model = models.SimulatedDataWorkspace
