"""Model definitions for the `workspaces` app."""

from anvil_consortium_manager.models import BaseWorkspaceData
from django_extensions.db.models import TimeStampedModel
from simple_history.models import HistoricalRecords


class SimulatedDataWorkspace(TimeStampedModel, BaseWorkspaceData):
    """A model to track simulated data workspaces."""

    history = HistoricalRecords()

    def __str__(self):
        return self.workspace.__str__()
