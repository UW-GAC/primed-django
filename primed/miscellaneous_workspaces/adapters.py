"""Adapters for the `workspaces` app."""

from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter
from anvil_consortium_manager.forms import WorkspaceForm

from primed.primed_anvil.adapters import WorkspaceAdminSharingAdapter
from primed.primed_anvil.tables import (
    DefaultWorkspaceStaffTable,
    DefaultWorkspaceUserTable,
)

from . import forms, models, tables


class SimulatedDataWorkspaceAdapter(WorkspaceAdminSharingAdapter, BaseWorkspaceAdapter):
    """Adapter for SimulatedDataWorkspaces."""

    type = "simulated_data"
    name = "Simulated Data workspace"
    description = "Workspaces containing simulated data"
    list_table_class_staff_view = DefaultWorkspaceStaffTable
    list_table_class_view = DefaultWorkspaceUserTable
    workspace_form_class = WorkspaceForm
    workspace_data_model = models.SimulatedDataWorkspace
    workspace_data_form_class = forms.SimulatedDataWorkspaceForm
    workspace_detail_template_name = "miscellaneous_workspaces/simulateddataworkspace_detail.html"


class ConsortiumDevelWorkspaceAdapter(WorkspaceAdminSharingAdapter, BaseWorkspaceAdapter):
    """Adapter for ConsortiumDevelWorkspaces."""

    type = "devel"
    name = "Consortium development workspace"
    description = "Workspaces intended for consortium development of methods"
    list_table_class_staff_view = DefaultWorkspaceStaffTable
    list_table_class_view = DefaultWorkspaceUserTable
    workspace_form_class = WorkspaceForm
    workspace_data_model = models.ConsortiumDevelWorkspace
    workspace_data_form_class = forms.ConsortiumDevelWorkspaceForm
    workspace_detail_template_name = "anvil_consortium_manager/workspace_detail.html"


class ResourceWorkspaceAdapter(WorkspaceAdminSharingAdapter, BaseWorkspaceAdapter):
    """Adapter for ResourceWorkspaces."""

    type = "resource"
    name = "Resource workspace"
    description = "Workspaces containing consortium resources (e.g., examples of using AnVIL, data inventories)"
    list_table_class_staff_view = DefaultWorkspaceStaffTable
    list_table_class_view = DefaultWorkspaceUserTable
    workspace_form_class = WorkspaceForm
    workspace_data_model = models.ResourceWorkspace
    workspace_data_form_class = forms.ResourceWorkspaceForm
    workspace_detail_template_name = "anvil_consortium_manager/workspace_detail.html"


class TemplateWorkspaceAdapter(WorkspaceAdminSharingAdapter, BaseWorkspaceAdapter):
    """Adapter for TemplateWorkspaces."""

    type = "template"
    name = "Template workspace"
    description = "Template workspaces that will be cloned by the CC to create other workspaces"
    list_table_class_staff_view = DefaultWorkspaceStaffTable
    list_table_class_view = DefaultWorkspaceUserTable
    workspace_form_class = WorkspaceForm
    workspace_data_model = models.TemplateWorkspace
    workspace_data_form_class = forms.TemplateWorkspaceForm
    workspace_detail_template_name = "anvil_consortium_manager/workspace_detail.html"


class OpenAccessWorkspaceAdapter(WorkspaceAdminSharingAdapter, BaseWorkspaceAdapter):
    """Adapter for TemplateWorkspaces."""

    type = "open_access"
    name = "Open access workspace"
    description = "Workspaces containing open access data"
    list_table_class_staff_view = tables.OpenAccessWorkspaceStaffTable
    list_table_class_view = tables.OpenAccessWorkspaceUserTable
    workspace_form_class = WorkspaceForm
    workspace_data_model = models.OpenAccessWorkspace
    workspace_data_form_class = forms.OpenAccessWorkspaceForm
    workspace_detail_template_name = "miscellaneous_workspaces/openaccessworkspace_detail.html"


class DataPrepWorkspaceAdapter(WorkspaceAdminSharingAdapter, BaseWorkspaceAdapter):
    """Adapter for DataPrepWorkspace."""

    type = "data_prep"
    name = "Data prep workspace"
    description = "Workspaces used to prepare data for sharing or update data that is already shared"
    list_table_class_staff_view = tables.DataPrepWorkspaceStaffTable
    list_table_class_view = tables.DataPrepWorkspaceUserTable
    workspace_form_class = WorkspaceForm
    workspace_data_model = models.DataPrepWorkspace
    workspace_data_form_class = forms.DataPrepWorkspaceForm
    workspace_detail_template_name = "miscellaneous_workspaces/dataprepworkspace_detail.html"
