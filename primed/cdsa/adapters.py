from anvil_consortium_manager.adapters.mixins import WorkspaceSharingAdapterMixin
from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter
from anvil_consortium_manager.models import Workspace

from primed.miscellaneous_workspaces.tables import DataPrepWorkspaceUserTable
from primed.primed_anvil.adapters import (
    PrimedWorkspacePermissions,
    WorkspaceAuthDomainAdapterMixin,
)
from primed.primed_anvil.forms import WorkspaceAuthDomainDisabledForm

from . import forms, models, tables


class CDSAWorkspaceAdapter(
    WorkspaceAuthDomainAdapterMixin,
    WorkspaceSharingAdapterMixin,
    BaseWorkspaceAdapter,
):
    """Adapter for CDSAWorkspaces."""

    type = "cdsa"
    name = "CDSA workspace"
    description = "Workspaces containing data from the Consortium Data Sharing Agreement"
    list_table_class_staff_view = tables.CDSAWorkspaceStaffTable
    list_table_class_view = tables.CDSAWorkspaceUserTable
    workspace_form_class = WorkspaceAuthDomainDisabledForm
    workspace_data_model = models.CDSAWorkspace
    workspace_data_form_class = forms.CDSAWorkspaceForm
    workspace_detail_template_name = "cdsa/cdsaworkspace_detail.html"
    share_permissions = [PrimedWorkspacePermissions.PRIMED_CC_ADMIN, PrimedWorkspacePermissions.PRIMED_CC_WRITER]

    def get_extra_detail_context_data(self, workspace, request):
        extra_context = {}
        associated_data_prep = Workspace.objects.filter(dataprepworkspace__target_workspace=workspace)
        extra_context["associated_data_prep_workspaces"] = DataPrepWorkspaceUserTable(associated_data_prep)
        extra_context["data_prep_active"] = associated_data_prep.filter(dataprepworkspace__is_active=True).exists()
        # Get the primary CDSA for this study, assuming it exists.
        try:
            extra_context["primary_cdsa"] = workspace.cdsaworkspace.get_primary_cdsa()
        except models.DataAffiliateAgreement.DoesNotExist:
            extra_context["primary_cdsa"] = None

        return extra_context
