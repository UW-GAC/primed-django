from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter
from anvil_consortium_manager.models import Workspace

from primed.miscellaneous_workspaces.tables import DataPrepWorkspaceUserTable
from primed.primed_anvil.adapters import WorkspaceAdminSharingAdapterMixin, WorkspaceAuthDomainAdapterMixin
from primed.primed_anvil.forms import WorkspaceAuthDomainDisabledForm

from . import forms, models, tables


class dbGaPWorkspaceAdapter(WorkspaceAuthDomainAdapterMixin, WorkspaceAdminSharingAdapterMixin, BaseWorkspaceAdapter):
    """Adapter for dbGaPWorkspaces."""

    type = "dbgap"
    name = "dbGaP workspace"
    description = "Workspaces containing data from released dbGaP accessions"
    list_table_class_staff_view = tables.dbGaPWorkspaceStaffTable
    list_table_class_view = tables.dbGaPWorkspaceUserTable
    workspace_form_class = WorkspaceAuthDomainDisabledForm
    workspace_data_model = models.dbGaPWorkspace
    workspace_data_form_class = forms.dbGaPWorkspaceForm
    workspace_detail_template_name = "dbgap/dbgapworkspace_detail.html"

    def get_extra_detail_context_data(self, workspace, request):
        extra_context = {}
        associated_data_prep = Workspace.objects.filter(dataprepworkspace__target_workspace=workspace)
        extra_context["associated_data_prep_workspaces"] = DataPrepWorkspaceUserTable(associated_data_prep)
        extra_context["data_prep_active"] = associated_data_prep.filter(dataprepworkspace__is_active=True).exists()
        return extra_context
