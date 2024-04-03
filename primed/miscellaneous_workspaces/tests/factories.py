from anvil_consortium_manager.tests.factories import WorkspaceFactory
from factory import Faker, SubFactory
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


class ResourceWorkspaceFactory(DjangoModelFactory):
    """A factory for the ResourceWorkspace model."""

    workspace = SubFactory(
        WorkspaceFactory,
        workspace_type=adapters.ResourceWorkspaceAdapter().get_type(),
    )
    requested_by = SubFactory(UserFactory)

    class Meta:
        model = models.ResourceWorkspace


class TemplateWorkspaceFactory(DjangoModelFactory):
    """A factory for the TemplateWorkspace model."""

    workspace = SubFactory(
        WorkspaceFactory,
        workspace_type=adapters.TemplateWorkspaceAdapter().get_type(),
    )
    intended_usage = Faker("sentence")

    class Meta:
        model = models.TemplateWorkspace


class OpenAccessWorkspaceFactory(DjangoModelFactory):
    """A factory for the OpenAccessWorkspace model."""

    workspace = SubFactory(WorkspaceFactory, workspace_type="open_access")
    requested_by = SubFactory(UserFactory)
    data_source = Faker("paragraph")

    class Meta:
        model = models.OpenAccessWorkspace


class DataPrepWorkspaceFactory(DjangoModelFactory):
    """A factory for the DataPrepWorkspace model."""

    workspace = SubFactory(WorkspaceFactory, workspace_type="data_prep")
    target_workspace = SubFactory(WorkspaceFactory)
    requested_by = SubFactory(UserFactory)

    class Meta:
        model = models.DataPrepWorkspace
