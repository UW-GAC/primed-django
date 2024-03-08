from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter
from anvil_consortium_manager.forms import WorkspaceForm
from anvil_consortium_manager.models import Workspace

from primed.miscellaneous_workspaces.tables import DataPrepWorkspaceTable

from . import forms, models, tables


class dbGaPWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for dbGaPWorkspaces."""

    type = "dbgap"
    name = "dbGaP workspace"
    description = "Workspaces containing data from released dbGaP accessions"
    list_table_class_staff_view = tables.dbGaPWorkspaceStaffTable
    list_table_class_view = tables.dbGaPWorkspaceUserTable
    workspace_form_class = WorkspaceForm
    workspace_data_model = models.dbGaPWorkspace
    workspace_data_form_class = forms.dbGaPWorkspaceForm
    workspace_detail_template_name = "dbgap/dbgapworkspace_detail.html"

    def get_extra_detail_context_data(self, workspace, request):
        extra_context = {}
        associated_data_prep = Workspace.objects.filter(
            dataprepworkspace__target_workspace=workspace
        )
        extra_context["associated_data_prep_workspace"] = DataPrepWorkspaceTable(
            associated_data_prep
        )
        return extra_context
