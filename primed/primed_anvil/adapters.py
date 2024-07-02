from anvil_consortium_manager.adapters.account import BaseAccountAdapter
from anvil_consortium_manager.models import (
    GroupGroupMembership,
    ManagedGroup,
    WorkspaceGroupSharing,
)
from django.conf import settings
from django.db.models import Q

from .filters import AccountListFilter
from .tables import AccountTable


class AccountAdapter(BaseAccountAdapter):
    """Custom account adapter for PRIMED."""

    list_table_class = AccountTable
    list_filterset_class = AccountListFilter

    def get_autocomplete_queryset(self, queryset, q):
        """Filter to Accounts where the email or the associated user name matches the query `q`."""
        if q:
            queryset = queryset.filter(Q(email__icontains=q) | Q(user__name__icontains=q))
        return queryset

    def get_autocomplete_label(self, account):
        """Adapter to provide a label for an account in autocomplete views."""
        if account.user:
            name = account.user.name
        else:
            name = "---"
        return "{} ({})".format(name, account.email)


class WorkspaceAuthDomainAdapter:
    """Helper class to add auth domains to workspaces."""

    def before_anvil_create(self, workspace):
        """Add authorization domain to workspace."""
        # Create the auth domain for the workspace.
        super().before_anvil_create(workspace)
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


class WorkspaceAdminSharingAdapter:
    """Helper class to share workspaces with the PRIMED_CC_ADMINs group."""

    def after_anvil_create(self, workspace):
        super().after_anvil_create(workspace)
        # Share the workspace with the ADMINs group as an owner.
        admins_group = ManagedGroup.objects.get(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)
        sharing = WorkspaceGroupSharing.objects.create(
            workspace=workspace,
            group=admins_group,
            access=WorkspaceGroupSharing.OWNER,
            can_compute=True,
        )
        sharing.anvil_create_or_update()
