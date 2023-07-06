from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter

from . import forms, models, tables


class CDSAWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for CDSAWorkspaces."""

    type = "cdsa"
    name = "CDSA workspace"
    description = (
        "Workspaces containing data from the Consortium Data Sharing Agreement."
    )
    list_table_class = tables.CDSAWorkspaceTable
    workspace_data_model = models.CDSAWorkspace
    workspace_data_form_class = forms.CDSAWorkspaceForm
    workspace_detail_template_name = "cdsa/cdsaworkspace_detail.html"
