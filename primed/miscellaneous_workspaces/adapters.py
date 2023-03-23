"""Adapters for the `workspaces` app."""

from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter
from anvil_consortium_manager.tables import WorkspaceTable

from . import forms, models, tables


class SimulatedDataWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for SimulatedDataWorkspaces."""

    type = "simulated_data"
    name = "Simulated Data workspace"
    description = "Workspaces containing simulated data"
    list_table_class = WorkspaceTable
    workspace_data_model = models.SimulatedDataWorkspace
    workspace_data_form_class = forms.SimulatedDataWorkspaceForm
    workspace_detail_template_name = (
        "miscellaneous_workspaces/simulateddataworkspace_detail.html"
    )


class ConsortiumDevelWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for ConsortiumDevelWorkspaces."""

    type = "devel"
    name = "Consortium development workspace"
    description = "Workspaces intended for consortium development of methods"
    list_table_class = WorkspaceTable
    workspace_data_model = models.ConsortiumDevelWorkspace
    workspace_data_form_class = forms.ConsortiumDevelWorkspaceForm
    workspace_detail_template_name = "anvil_consortium_manager/workspace_detail.html"


class ExampleWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for ExampleWorkspaces."""

    type = "example"
    name = "Example workspace"
    description = (
        "Workspaces containing examples of using AnVIL, working with data, etc."
    )
    list_table_class = WorkspaceTable
    workspace_data_model = models.ExampleWorkspace
    workspace_data_form_class = forms.ExampleWorkspaceForm
    workspace_detail_template_name = "anvil_consortium_manager/workspace_detail.html"


class TemplateWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for TemplateWorkspaces."""

    type = "template"
    name = "Template workspace"
    description = "Template workspaces that can be cloned to create other workspaces"
    list_table_class = WorkspaceTable
    workspace_data_model = models.TemplateWorkspace
    workspace_data_form_class = forms.TemplateWorkspaceForm
    workspace_detail_template_name = "anvil_consortium_manager/workspace_detail.html"


class OpenAccessWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for TemplateWorkspaces."""

    type = "open_access"
    name = "Open access workspace"
    description = "Workspaces containing open access data"
    list_table_class = tables.OpenAccessWorkspaceTable
    workspace_data_model = models.OpenAccessWorkspace
    workspace_data_form_class = forms.OpenAccessWorkspaceForm
    workspace_detail_template_name = (
        "miscellaneous_workspaces/openaccessworkspace_detail.html"
    )
