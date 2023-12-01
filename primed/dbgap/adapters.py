from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter
from anvil_consortium_manager.forms import WorkspaceForm

from . import forms, models, tables


class dbGaPWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for dbGaPWorkspaces."""

    type = "dbgap"
    name = "dbGaP workspace"
    description = "Workspaces containing data from released dbGaP accessions"
    list_table_class_staff_view = tables.dbGaPWorkspaceTable
    list_table_class_view = tables.dbGaPWorkspaceTable
    workspace_form_class = WorkspaceForm
    workspace_data_model = models.dbGaPWorkspace
    workspace_data_form_class = forms.dbGaPWorkspaceForm
    workspace_detail_template_name = "dbgap/dbgapworkspace_detail.html"
