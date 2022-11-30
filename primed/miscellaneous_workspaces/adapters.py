"""Adapters for the `workspaces` app."""

from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter
from anvil_consortium_manager.tables import WorkspaceTable

from . import forms, models


class SimulatedDataWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for SimulatedDataWorkspaces."""

    type = "simulated_data"
    name = "Simulated Data workspace"
    list_table_class = WorkspaceTable
    workspace_data_model = models.SimulatedDataWorkspace
    workspace_data_form_class = forms.SimulatedDataWorkspaceForm
    workspace_detail_template_name = (
        "miscellaneous_workspaces/simulateddataworkspace_detail.html"
    )


class ConsortiumDevelWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for SimulatedDataWorkspaces."""

    type = "devel"
    name = "Consortium development workspace"
    list_table_class = WorkspaceTable
    workspace_data_model = models.ConsortiumDevelWorkspace
    workspace_data_form_class = forms.ConsortiumDevelWorkspaceForm
    workspace_detail_template_name = "anvil_consortium_manager/workspace_detail.html"
