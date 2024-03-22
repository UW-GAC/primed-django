"""Model definitions for the `miscellaneous_workspaces` app."""

from anvil_consortium_manager.models import BaseWorkspaceData, Workspace
from django.core.exceptions import ValidationError
from django.db import models
from django_extensions.db.models import TimeStampedModel

from primed.primed_anvil.models import AvailableData, RequesterModel, Study


class SimulatedDataWorkspace(RequesterModel, TimeStampedModel, BaseWorkspaceData):
    """A model to track simulated data workspaces."""


class ConsortiumDevelWorkspace(RequesterModel, TimeStampedModel, BaseWorkspaceData):
    """A model to track shared consortium development workspaces."""


class ResourceWorkspace(RequesterModel, TimeStampedModel, BaseWorkspaceData):
    """A model to track resource workspaces."""


class TemplateWorkspace(TimeStampedModel, BaseWorkspaceData):
    """A model to track template workspaces."""

    intended_usage = models.TextField()


class OpenAccessWorkspace(RequesterModel, TimeStampedModel, BaseWorkspaceData):
    """A model to track workspaces containing open access data (e.g., UKBB GSR, 1000 Genomes)."""

    studies = models.ManyToManyField(
        Study,
        help_text="The studies associated with this workspace.",
    )
    data_source = models.TextField()
    data_url = models.URLField(verbose_name="data URL", blank=True, max_length=255)
    available_data = models.ManyToManyField(
        AvailableData,
        help_text="The types of data available in this workspace.",
        blank=True,
    )


class DataPrepWorkspace(RequesterModel, TimeStampedModel, BaseWorkspaceData):
    """A model to track workspaces that are used to update data in another workspace."""

    target_workspace = models.ForeignKey(
        Workspace,
        on_delete=models.PROTECT,
        related_name="data_prep_workspaces",
        help_text="The workspace for which data is being prepared or updated.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indicator of whether this workspace is currently being used to prepare data.",
    )

    def clean(self):
        if hasattr(self, "target_workspace"):
            if self.target_workspace.workspace_type == "data_prep":
                raise ValidationError(
                    {
                        "target_workspace": "target_workspace cannot be a DataPrepWorkspace."
                    }
                )

        if hasattr(self, "target_workspace") and hasattr(self, "workspace"):
            if self.target_workspace == self.workspace:
                raise ValidationError(
                    {
                        "target_workspace": "target_workspace must be different than workspace."
                    }
                )
