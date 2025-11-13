from anvil_consortium_manager.adapters.account import BaseAccountAdapter
from anvil_consortium_manager.adapters.managed_group import BaseManagedGroupAdapter
from anvil_consortium_manager.models import (
    GroupGroupMembership,
    ManagedGroup,
    WorkspaceGroupSharing,
)
from anvil_consortium_manager.tables import ManagedGroupStaffTable
from django.conf import settings
from django.db.models import Q

from .filters import AccountListFilter
from .tables import AccountTable


class AccountAdapter(BaseAccountAdapter):
    """Custom account adapter for PRIMED."""

    list_table_class = AccountTable
    list_filterset_class = AccountListFilter
    account_link_verify_message = """Thank you for linking your account!
    The CC will add your account to appropriate groups on AnVIL.
    If you do not have access to workspaces that you expect after 24 hours, please contact the CC."""
    account_link_verify_redirect = "users:redirect"
    account_link_email_subject = "Verify your AnVIL account email"
    account_verification_notification_email = "primedconsortium@uw.edu"

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


class WorkspaceAuthDomainAdapterMixin:
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
        try:
            admins_group = ManagedGroup.objects.get(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)
        except ManagedGroup.DoesNotExist:
            return
        membership = GroupGroupMembership.objects.create(
            parent_group=auth_domain,
            child_group=admins_group,
            role=GroupGroupMembership.ADMIN,
        )
        membership.anvil_create()


class WorkspaceSharingAdapterMixin:
    def _after_anvil_create_share(self, workspace, group_name, share_permission, can_compute):
        try:
            admins_group = ManagedGroup.objects.get(name=group_name)
        except ManagedGroup.DoesNotExist:
            return
        sharing = WorkspaceGroupSharing.objects.create(
            workspace=workspace,
            group=admins_group,
            access=share_permission,
            can_compute=can_compute,
        )
        sharing.anvil_create_or_update()

    def _after_anvil_import_share(self, workspace, group_name, share_permission, can_compute):
        try:
            admins_group = ManagedGroup.objects.get(name=group_name)
        except ManagedGroup.DoesNotExist:
            return
        try:
            sharing = WorkspaceGroupSharing.objects.get(
                workspace=workspace,
                group=admins_group,
            )
        except WorkspaceGroupSharing.DoesNotExist:
            sharing = WorkspaceGroupSharing.objects.create(
                workspace=workspace,
                group=admins_group,
                access=share_permission,
                can_compute=can_compute,
            )
            sharing.save()
            sharing.anvil_create_or_update()
        else:
            # If the existing sharing record exists, make sure it has the correct permissions.
            if sharing.can_compute != can_compute or sharing.access != share_permission:
                sharing.can_compute = can_compute
                sharing.access = share_permission
                sharing.save()
                sharing.anvil_create_or_update()


class WorkspaceAdminSharingAdapterMixin(WorkspaceSharingAdapterMixin):
    """Helper class to share workspaces with the PRIMED_CC_ADMINs group."""

    workspace_share_permission = WorkspaceGroupSharing.OWNER
    workspace_share_can_compute = True

    # This needs to be a property as tests override the setting
    # so you cannot set at the class level
    @property
    def workspace_share_group(self) -> str:
        return settings.ANVIL_CC_ADMINS_GROUP_NAME

    def after_anvil_create(self, workspace):
        self._after_anvil_create_share(
            workspace=workspace,
            group_name=self.workspace_share_group,
            share_permission=self.workspace_share_permission,
            can_compute=self.workspace_share_can_compute,
        )
        super().after_anvil_create(workspace)

    def after_anvil_import(self, workspace):
        self._after_anvil_import_share(
            workspace=workspace,
            group_name=self.workspace_share_group,
            share_permission=self.workspace_share_permission,
            can_compute=self.workspace_share_can_compute,
        )
        super().after_anvil_import(workspace)


class WorkspaceWriterSharingAdapterMixin(WorkspaceSharingAdapterMixin):
    """Helper class to share workspaces with the PRIMED_CC_WRITERs group."""

    workspace_writer_share_permission = WorkspaceGroupSharing.WRITER
    workspace_writer_share_can_compute = True

    # This needs to be a property as tests override the setting
    # so you cannot set at the class level
    @property
    def workspace_writer_share_group(self) -> str:
        return settings.ANVIL_CC_WRITERS_GROUP_NAME

    def after_anvil_create(self, workspace):
        self._after_anvil_create_share(
            workspace=workspace,
            group_name=self.workspace_writer_share_group,
            share_permission=WorkspaceWriterSharingAdapterMixin.workspace_writer_share_permission,
            can_compute=WorkspaceWriterSharingAdapterMixin.workspace_writer_share_can_compute,
        )
        super().after_anvil_create(workspace)

    def after_anvil_import(self, workspace):
        self._after_anvil_import_share(
            workspace=workspace,
            group_name=self.workspace_writer_share_group,
            share_permission=WorkspaceWriterSharingAdapterMixin.workspace_writer_share_permission,
            can_compute=WorkspaceWriterSharingAdapterMixin.workspace_writer_share_can_compute,
        )
        super().after_anvil_import(workspace)


class ManagedGroupAdapter(BaseManagedGroupAdapter):
    """Adapter for ManagedGroups."""

    list_table_class = ManagedGroupStaffTable

    def after_anvil_create(self, managed_group):
        super().after_anvil_create(managed_group)
        # Add the ADMINs group as an admin of the auth domain.
        try:
            admins_group = ManagedGroup.objects.get(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)
        except ManagedGroup.DoesNotExist:
            return
        membership = GroupGroupMembership.objects.create(
            parent_group=managed_group,
            child_group=admins_group,
            role=GroupGroupMembership.ADMIN,
        )
        membership.anvil_create()
