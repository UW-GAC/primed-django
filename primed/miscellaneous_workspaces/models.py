"""Model definitions for the `miscellaneous_workspaces` app."""

from anvil_consortium_manager.adapters.workspace import workspace_adapter_registry
from anvil_consortium_manager.models import BaseWorkspaceData
from django.core.exceptions import ValidationError
from django.db import models
from django_extensions.db.models import TimeStampedModel
from simple_history.models import HistoricalRecords


class SimulatedDataWorkspace(TimeStampedModel, BaseWorkspaceData):
    """A model to track simulated data workspaces."""

    history = HistoricalRecords()

    def __str__(self):
        return self.workspace.__str__()


class ConsortiumDevelWorkspace(TimeStampedModel, BaseWorkspaceData):
    """A model to track shared consortium development workspaces."""

    history = HistoricalRecords()

    def __str__(self):
        return self.workspace.__str__()


class ExampleWorkspace(TimeStampedModel, BaseWorkspaceData):
    """A model to track example workspaces."""

    history = HistoricalRecords()

    def __str__(self):
        return self.workspace.__str__()


class TemplateWorkspace(TimeStampedModel, BaseWorkspaceData):
    """A model to track template workspaces."""

    intended_workspace_type = models.CharField(max_length=63)

    history = HistoricalRecords()

    def __str__(self):
        return self.workspace.__str__()

    def clean(self):
        """Custom cleaning checks.

        - Verify that intended_workspace_type is one of the registered types, excluding this type."""
        registered_workspace_types = workspace_adapter_registry.get_registered_names()
        if self.intended_workspace_type:
            if self.intended_workspace_type not in registered_workspace_types:
                raise ValidationError(
                    {
                        "intended_workspace_type": "intended_workspace_type must be one of the registered types."
                    }
                )
            # We cannot import the adapter here because it would lead to a circular import, but we don't want
            # to create a template workspace for TemplateWorkspaces. So check if the type is not "template".
            elif self.intended_workspace_type == "template":
                raise ValidationError(
                    {
                        "intended_workspace_type": "intended_workspace_type may not be 'template'."
                    }
                )
