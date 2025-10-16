from anvil_consortium_manager.adapters.account import BaseAccountAdapter
from anvil_consortium_manager.adapters.managed_group import BaseManagedGroupAdapter
from anvil_consortium_manager.models import (
    GroupAccountMembership,
    GroupGroupMembership,
    ManagedGroup,
    WorkspaceGroupSharing,
)
from anvil_consortium_manager.tables import ManagedGroupStaffTable
from django.conf import settings
from django.db.models import Q

from .filters import AccountListFilter
from .models import StudySite
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

    def after_account_verification(self, account):
        """Add the account to the member group for any StudySites that they are a part of."""
        super().after_account_verification(account)
        # Add the user to member groups for any StudySites that they are a part of.
        study_sites = StudySite.objects.select_related("member_group").filter(member_group__isnull=False)
        for site in study_sites:
            if site.member_group:
                self._add_account_to_group(account, site.member_group)

        user = account.user
        # Add the user to any dbGaP access groups that they are associated with.
        pi_apps = user.pi_dbgap_applications.select_related("anvil_access_group").all()
        collab_apps = user.collaborator_dbgap_applications.select_related("anvil_access_group").all()
        dbgap_applications = set(pi_apps) | set(collab_apps)
        for app in dbgap_applications:
            if app.anvil_access_group:
                self._add_account_to_group(account, app.anvil_access_group)

        # Add the user to any CDSA SignedAgreement access groups that they are associated with.
        signed_agreements = user.accessor_signed_agreements.select_related("anvil_access_group").all()
        for sa in signed_agreements:
            if sa.anvil_access_group:
                self._add_account_to_group(account, sa.anvil_access_group)

        # Add the user to DataAffiliateAgreement uploader groups that they are associated with.
        data_affiliate_agreements = user.uploader_signed_agreements.select_related("anvil_upload_group").all()
        for daa in data_affiliate_agreements:
            if daa.anvil_upload_group:
                self._add_account_to_group(account, daa.anvil_upload_group)

    def _add_account_to_group(self, account, group):
        if not GroupAccountMembership.objects.filter(group=group, account=account).exists():
            membership = GroupAccountMembership(
                group=group,
                account=account,
                role=GroupAccountMembership.MEMBER,
            )
            membership.save()
            membership.anvil_create()


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


class WorkspaceAdminSharingAdapterMixin:
    """Helper class to share workspaces with the PRIMED_CC_ADMINs group."""

    def after_anvil_create(self, workspace):
        super().after_anvil_create(workspace)
        # Share the workspace with the ADMINs group as an owner.
        try:
            admins_group = ManagedGroup.objects.get(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)
        except ManagedGroup.DoesNotExist:
            return
        sharing = WorkspaceGroupSharing.objects.create(
            workspace=workspace,
            group=admins_group,
            access=WorkspaceGroupSharing.OWNER,
            can_compute=True,
        )
        sharing.anvil_create_or_update()

    def after_anvil_import(self, workspace):
        super().after_anvil_import(workspace)
        # # Check if the workspace is already shared with the ADMINs group.
        try:
            admins_group = ManagedGroup.objects.get(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)
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
                access=WorkspaceGroupSharing.OWNER,
                can_compute=True,
            )
            sharing.save()
            sharing.anvil_create_or_update()
        else:
            # If the existing sharing record exists, make sure it has the correct permissions.
            if not sharing.can_compute or sharing.access != WorkspaceGroupSharing.OWNER:
                sharing.can_compute = True
                sharing.access = WorkspaceGroupSharing.OWNER
                sharing.save()
                sharing.anvil_create_or_update()


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
