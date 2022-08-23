from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter

from . import forms, models, tables


class dbGaPWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for dbGaPWorkspaces."""

    type = "dbGaP"
    name = "dbGaP workspace"
    list_table_class = tables.dbGaPWorkspaceTable
    workspace_data_model = models.dbGaPWorkspace
    workspace_data_form_class = forms.dbGaPWorkspaceForm
