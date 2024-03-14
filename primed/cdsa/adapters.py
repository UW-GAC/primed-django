from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter
from anvil_consortium_manager.forms import WorkspaceForm

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
        # Get the primary CDSA for this study, assuming it exists.
        extra_context = {}
        # Data use limitations from CDSA
        try:
            extra_context["primary_cdsa"] = workspace.cdsaworkspace.get_primary_cdsa()
        except models.DataAffiliateAgreement.DoesNotExist:
            extra_context["primary_cdsa"] = None

        return extra_context
