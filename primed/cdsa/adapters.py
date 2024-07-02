from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter
from anvil_consortium_manager.models import GroupGroupMembership, ManagedGroup, Workspace, WorkspaceGroupSharing
from django.conf import settings

from primed.miscellaneous_workspaces.tables import DataPrepWorkspaceUserTable
from primed.primed_anvil.forms import WorkspaceAuthDomainDisabledForm

from . import forms, models, tables


class CDSAWorkspaceAdapter(BaseWorkspaceAdapter):
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

    def before_workspace_create(self, workspace):
        # Create the auth domain for the workspace.
        """Add authorization domain to workspace."""
        auth_domain_name = "AUTH_" + workspace.name
        auth_domain = ManagedGroup.objects.create(
            name=auth_domain_name,
            is_managed_by_app=True,
            email=auth_domain_name + "@firecloud.org",
        )
        workspace.authorization_domains.add(auth_domain)
        auth_domain.anvil_create()
        # Add the ADMINs group as an admin of the auth domain.
        admins_group = ManagedGroup.objects.get(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)
        membership = GroupGroupMembership.objects.create(
            parent_group=auth_domain,
            child_group=admins_group,
            role=GroupGroupMembership.ADMIN,
        )
        membership.anvil_create()

    def after_workspace_create(self, workspace):
        # Add the ADMINs group as an owner of the workspace.
        admins_group = ManagedGroup.objects.get(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)
        sharing = WorkspaceGroupSharing.objects.create(
            workspace=workspace,
            group=admins_group,
            access=WorkspaceGroupSharing.OWNER,
            can_compute=True,
        )
        sharing.anvil_create_or_update()
