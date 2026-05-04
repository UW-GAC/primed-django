from dataclasses import dataclass
from typing import Union

import django_tables2 as tables
from anvil_consortium_manager.models import (
    Account,
    GroupAccountMembership,
    GroupGroupMembership,
    ManagedGroup,
)
from django.conf import settings
from django.urls import reverse

from primed.primed_anvil.audit import PRIMEDAudit, PRIMEDAuditResult
from primed.primed_anvil.tables import BooleanIconColumn

from . import models


@dataclass
class AccessAuditResult(PRIMEDAuditResult):
    """Base class to hold the result of an access audit for a CollaborativeAnalysisWorkspace."""

    collaborative_analysis_workspace: models.CollaborativeAnalysisWorkspace
    member: Union[Account, ManagedGroup]
    note: str
    has_access: bool
    action: str = None

    def get_action_url(self):
        return reverse(
            "collaborative_analysis:audit:resolve",
            args=[
                self.collaborative_analysis_workspace.workspace.billing_project.name,
                self.collaborative_analysis_workspace.workspace.name,
                self.member.email,
            ],
        )

    def get_table_dictionary(self):
        """Return a dictionary that can be used to populate an instance of `SignedAgreementAccessAuditTable`."""
        row = {
            "workspace": self.collaborative_analysis_workspace,
            "member": self.member,
            "has_access": self.has_access,
            "note": self.note,
            "action": self.action,
            "action_url": self.get_action_url(),
        }
        return row


@dataclass
class VerifiedAccess(AccessAuditResult):
    """Audit results class for when an account has verified access."""

    has_access: bool = True

    def __str__(self):
        return f"Verified access: {self.note}"


@dataclass
class VerifiedNoAccess(AccessAuditResult):
    """Audit results class for when an account has verified no access."""

    has_access: bool = False

    def __str__(self):
        return f"Verified no access: {self.note}"


@dataclass
class GrantAccess(AccessAuditResult):
    """Audit results class for when an account should be granted access."""

    has_access: bool = False
    action: str = "Grant access"

    def __str__(self):
        return f"Grant access: {self.note}"


@dataclass
class RemoveAccess(AccessAuditResult):
    """Audit results class for when access for an account should be removed."""

    has_access: bool = True
    action: str = "Remove access"

    def __str__(self):
        return f"Remove access: {self.note}"


class AccessAuditResultsTable(tables.Table):
    """A table to show results from a CollaborativeAnalysisWorkspaceAccessAudit instance."""

    workspace = tables.Column(linkify=True)
    member = tables.Column(linkify=True)
    has_access = BooleanIconColumn(show_false_icon=True)
    note = tables.Column()
    action = tables.TemplateColumn(
        template_name="collaborative_analysis/snippets/collaborativeanalysis_audit_action_button.html"
    )

    class Meta:
        attrs = {"class": "table align-middle"}


class CollaborativeAnalysisWorkspaceAccessAudit(PRIMEDAudit):
    """Class to audit access to a CollaborativeAnalysisWorkspace."""

    # Allowed reasons for access.
    IN_SOURCE_AUTH_DOMAINS = "Account is in all source auth domains managed by the app for this workspace."

    # Allowed reasons for no access.
    NOT_IN_SOURCE_AUTH_DOMAINS = "Account is not in all source auth domains for this workspace."
    NOT_IN_ANALYST_OR_CC_GROUP = "Account is not in the analyst or CC writer group for this workspace."
    INACTIVE_ACCOUNT = "Account is inactive."

    # Errors.
    UNEXPECTED_GROUP_ACCESS = "Unexpected group added to the auth domain."

    results_table_class = AccessAuditResultsTable

    def __init__(self, queryset=None):
        """Initialize the audit.

        Args:
            queryset: A queryset of CollaborativeAnalysisWorkspaces to audit.
        """
        super().__init__()
        if queryset is None:
            queryset = models.CollaborativeAnalysisWorkspace.objects.all()
        self.queryset = queryset

    def _audit_workspace(self, workspace):
        """Audit access to a single CollaborativeAnalysisWorkspace."""
        # Loop over analyst accounts for this workspace.
        # In the loop, run the _audit_workspace_and_account method.
        # Any remainig accounts in the auth domain that are not in the analyst group should be *errors*.
        analyst_group = workspace.analyst_group
        # CC group
        try:
            cc_group = ManagedGroup.objects.get(name=settings.ANVIL_CC_WRITERS_GROUP_NAME)
        except ManagedGroup.DoesNotExist:
            cc_group = None
            accounts = Account.objects.filter(groupaccountmembership__group=analyst_group).distinct()
            # GroupAccountMembership.objects.filter(group=analyst_group)
        else:
            accounts = Account.objects.filter(groupaccountmembership__group__in=[analyst_group, cc_group]).distinct()

        # Get a list of accounts in the auth domain.
        auth_domain_accounts = [
            x.account
            for x in GroupAccountMembership.objects.filter(group=workspace.workspace.authorization_domains.get())
        ]

        for account in accounts:
            self._audit_workspace_and_account(workspace, account)
            try:
                auth_domain_accounts.remove(account)
            except ValueError:
                # This is fine - this happens if the account is not in the auth domain.
                pass

        # Loop over remaining accounts in the auth domain.
        for account in auth_domain_accounts:
            # Should this be an error, or a needs_action?
            # eg if an analyst is removed on purpose, it should be needs_action.
            self.errors.append(
                RemoveAccess(
                    collaborative_analysis_workspace=workspace,
                    member=account,
                    note=self.NOT_IN_ANALYST_OR_CC_GROUP,
                )
            )

        # Check group access. Most groups should not have access.
        group_memberships = GroupGroupMembership.objects.filter(
            parent_group=workspace.workspace.authorization_domains.get(),
        ).exclude(
            # Ignore cc admins group - it is handled differently because it should have admin privileges.
            child_group__name=settings.ANVIL_CC_ADMINS_GROUP_NAME,
        )
        for membership in group_memberships:
            self._audit_workspace_and_group(workspace, membership.child_group)
        # # Audit allowed groups
        # for group in ManagedGroup.objects.filter(name__in=self.ALLOWED_GROUP_NAMES):
        #     self._audit_workspace_and_group(workspace, group)

    def _audit_workspace_and_group(self, collaborative_analysis_workspace, group):
        """Audit access for a specific CollaborativeAnalysisWorkspace and group."""
        in_auth_domain = collaborative_analysis_workspace.workspace.authorization_domains.get()
        auth_domain = collaborative_analysis_workspace.workspace.authorization_domains.get()
        in_auth_domain = GroupGroupMembership.objects.filter(parent_group=auth_domain, child_group=group).exists()
        if in_auth_domain:
            self.errors.append(
                RemoveAccess(
                    collaborative_analysis_workspace=collaborative_analysis_workspace,
                    member=group,
                    note=self.UNEXPECTED_GROUP_ACCESS,
                )
            )
        else:
            self.verified.append(
                VerifiedNoAccess(
                    collaborative_analysis_workspace=collaborative_analysis_workspace,
                    member=group,
                    note=self.NON_DCC_GROUP,
                )
            )

    def _audit_workspace_and_account(self, collaborative_analysis_workspace, account):
        """Audit access for a specific CollaborativeAnalysisWorkspace and account."""
        # Cases to consider:
        # - analyst is in all relevant source auth domains, and is in the workspace auth domain.
        # - analyst is in some but not all relevant source auth domains, and is in the workspace auth domain..
        # - analyst is in none of the relevant source auth domains, and is in the workspace auth domain..
        # - analyst is in all relevant source auth domains, and is not in the workspace auth domain.
        # - analyst is in some but not all relevant source auth domains, and is not in the workspace auth domain.
        # - analyst is in none of the relevant source auth domains, and is not in the workspace auth domain.
        # - an account is in the workspace auth domain, but is not in the analyst group.
        # Get all groups for the account.
        account_groups = account.get_all_groups()
        # Check whether the account is in the analyst group or any of the allowed CC groups.
        in_analyst_group = collaborative_analysis_workspace.analyst_group in account_groups
        in_allowed_cc_group = GroupAccountMembership.objects.filter(
            group__name__iexact=settings.ANVIL_CC_WRITERS_GROUP_NAME, account=account
        ).exists()
        in_allowed_group = in_analyst_group or in_allowed_cc_group
        # Check whether the account is in the auth domain of the collab workspace.
        in_auth_domain = collaborative_analysis_workspace.workspace.authorization_domains.get() in account_groups
        if in_allowed_group:
            # Check whether access is allowed. Start by assuming yes, and then
            # set to false if the account should not have access.
            access_allowed = True
            # Loop over all source workspaces.
            for source_workspace in collaborative_analysis_workspace.source_workspaces.all():
                # Loop over all auth domains for that source workspace.
                # Only include source auth domains that are managed by the app.
                # This is intended to handle the federal_data_lockdown auth domain.
                # We should have enough controls on who gets access that this is ok.
                for source_auth_domain in source_workspace.authorization_domains.filter(is_managed_by_app=True):
                    # If the user is not in the auth domain, they are not allowed to have access to the workspace.
                    # If so, break out of the loop - not necessary to check membership of the remaining auth domains.
                    # Note that this only breaks out of the inner loop.
                    # It would be more efficient to break out of the outer loop as well.
                    if source_auth_domain not in account_groups:
                        access_allowed = False
                        break
            if access_allowed and in_auth_domain:
                self.verified.append(
                    VerifiedAccess(
                        collaborative_analysis_workspace=collaborative_analysis_workspace,
                        member=account,
                        note=self.IN_SOURCE_AUTH_DOMAINS,
                    )
                )
            elif access_allowed and not in_auth_domain:
                self.needs_action.append(
                    GrantAccess(
                        collaborative_analysis_workspace=collaborative_analysis_workspace,
                        member=account,
                        note=self.IN_SOURCE_AUTH_DOMAINS,
                    )
                )
            elif not access_allowed and in_auth_domain:
                self.needs_action.append(
                    RemoveAccess(
                        collaborative_analysis_workspace=collaborative_analysis_workspace,
                        member=account,
                        note=self.NOT_IN_SOURCE_AUTH_DOMAINS,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        collaborative_analysis_workspace=collaborative_analysis_workspace,
                        member=account,
                        note=self.NOT_IN_SOURCE_AUTH_DOMAINS,
                    )
                )
        else:
            if in_auth_domain:
                self.needs_action.append(
                    RemoveAccess(
                        collaborative_analysis_workspace=collaborative_analysis_workspace,
                        member=account,
                        note=self.NOT_IN_ANALYST_OR_CC_GROUP,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        collaborative_analysis_workspace=collaborative_analysis_workspace,
                        member=account,
                        note=self.NOT_IN_ANALYST_OR_CC_GROUP,
                    )
                )

    def _run_audit(self):
        """Run the audit on the set of workspaces."""
        for workspace in self.queryset:
            self._audit_workspace(workspace)
