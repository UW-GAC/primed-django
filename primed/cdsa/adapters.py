from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter
from anvil_consortium_manager.forms import WorkspaceForm
from anvil_consortium_manager.models import Workspace

from primed.miscellaneous_workspaces.tables import DataPrepWorkspaceTable

from . import forms, models, tables


class CDSAWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for CDSAWorkspaces."""

    type = "cdsa"
    name = "CDSA workspace"
    description = (
        "Workspaces containing data from the Consortium Data Sharing Agreement"
    )
    list_table_class_staff_view = tables.CDSAWorkspaceStaffTable
    list_table_class_view = tables.CDSAWorkspaceUserTable
    workspace_form_class = WorkspaceForm
    workspace_data_model = models.CDSAWorkspace
    workspace_data_form_class = forms.CDSAWorkspaceForm
    workspace_detail_template_name = "cdsa/cdsaworkspace_detail.html"

    def get_extra_detail_context_data(self, workspace, request):
        extra_context = {}
        associated_data_prep = Workspace.objects.filter(
            dataprepworkspace__target_workspace=workspace
        )
        extra_context["associated_data_prep_workspaces"] = DataPrepWorkspaceTable(
            associated_data_prep
        )
        return extra_context
