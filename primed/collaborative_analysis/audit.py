from dataclasses import dataclass
from typing import Union

import django_tables2 as tables
from anvil_consortium_manager.models import (
    Account,
    GroupAccountMembership,
    GroupGroupMembership,
    ManagedGroup,
)
from django.urls import reverse
from django.utils.safestring import mark_safe

from primed.primed_anvil.tables import BooleanIconColumn

from . import models


@dataclass
class AccessAuditResult:
    """Base class to hold the result of an access audit for a CollaborativeAnalysisWorkspace."""

    collaborative_analysis_workspace: models.CollaborativeAnalysisWorkspace
    member: Union[Account, ManagedGroup]
    note: str
    has_access: bool

    def get_action_url(self):
        """The URL that handles the action needed."""
        return None

    def get_action(self):
        """An indicator of what action needs to be taken."""
        return None

    def get_table_dictionary(self):
        """Return a dictionary that can be used to populate an instance of `SignedAgreementAccessAuditTable`."""
        row = {
            "workspace": self.collaborative_analysis_workspace,
            "member": self.member,
            "has_access": self.has_access,
            "note": self.note,
            "action": self.get_action(),
            "action_url": self.get_action_url(),
        }
        return row


@dataclass
class VerifiedAccess(AccessAuditResult):
    """Audit results class for when an account has verified access."""

    has_access: bool = True


@dataclass
class VerifiedNoAccess(AccessAuditResult):
    """Audit results class for when an account has verified no access."""

    has_access: bool = False


@dataclass
class GrantAccess(AccessAuditResult):
    """Audit results class for when an account should be granted access."""

    has_access: bool = False

    def get_action(self):
        return "Grant access"

    def get_action_url(self):
        if isinstance(self.member, Account):
            return reverse(
                "anvil_consortium_manager:managed_groups:member_accounts:new_by_account",
                args=[
                    self.collaborative_analysis_workspace.workspace.authorization_domains.first().name,
                    self.member.uuid,
                ],
            )
        else:
            return reverse(
                "anvil_consortium_manager:managed_groups:member_groups:new_by_child",
                args=[
                    self.collaborative_analysis_workspace.workspace.authorization_domains.first().name,
                    self.member.name,
                ],
            )


@dataclass
class RemoveAccess(AccessAuditResult):
    """Audit results class for when access for an account should be removed."""

    has_access: bool = True

    def get_action(self):
        return "Remove access"

    def get_action_url(self):
        if isinstance(self.member, Account):
            return reverse(
                "anvil_consortium_manager:managed_groups:member_accounts:delete",
                args=[
                    self.collaborative_analysis_workspace.workspace.authorization_domains.first().name,
                    self.member.uuid,
                ],
            )
        else:
            return reverse(
                "anvil_consortium_manager:managed_groups:member_groups:delete",
                args=[
                    self.collaborative_analysis_workspace.workspace.authorization_domains.first().name,
                    self.member.name,
                ],
            )


class AccessAuditResultsTable(tables.Table):
    """A table to show results from a CollaborativeAnalysisWorkspaceAccessAudit instance."""

    workspace = tables.Column(linkify=True)
    member = tables.Column(linkify=True)
    has_access = BooleanIconColumn(show_false_icon=True)
    note = tables.Column()
    action = tables.Column()

    class Meta:
        attrs = {"class": "table align-middle"}

    def render_action(self, record, value):
        return mark_safe(
            """<a href="{}" class="btn btn-primary btn-sm">{}</a>""".format(
                record["action_url"], value
            )
        )


class CollaborativeAnalysisWorkspaceAccessAudit:
    """Class to audit access to a CollaborativeAnalysisWorkspace."""

    # Allowed reasons for access.
    IN_SOURCE_AUTH_DOMAINS = "Account is in all source auth domains for this workspace."
    DCC_ACCESS = "DCC groups are allowed access."

    # Allowed reasons for no access.
    NOT_IN_SOURCE_AUTH_DOMAINS = (
        "Account is not in all source auth domains for this workspace."
    )
    NOT_IN_ANALYST_GROUP = "Account is not in the analyst group for this workspace."
    INACTIVE_ACCOUNT = "Account is inactive."

    # Errors.
    UNEXPECTED_GROUP_ACCESS = "Unexpected group added to the auth domain."

    results_table_class = AccessAuditResultsTable

    def __init__(self, queryset=None):
        """Initialize the audit.

        Args:
            queryset: A queryset of CollaborativeAnalysisWorkspaces to audit.
        """
        if queryset is None:
            queryset = models.CollaborativeAnalysisWorkspace.objects.all()
        self.queryset = queryset
        self.verified = []
        self.needs_action = []
        self.errors = []
        self.completed = False

    def _audit_workspace(self, workspace):
        """Audit access to a single CollaborativeAnalysisWorkspace."""
        # Loop over analyst accounts for this workspace.
        # In the loop, run the _audit_workspace_and_account method.
        # Any remainig accounts in the auth domain that are not in the analyst group should be *errors*.
        analyst_group = workspace.analyst_group
        analyst_memberships = GroupAccountMembership.objects.filter(group=analyst_group)
        # Get a list of accounts in the auth domain.
        auth_domain_membership = [
            x.account
            for x in GroupAccountMembership.objects.filter(
                group=workspace.workspace.authorization_domains.first()
            )
        ]
        for membership in analyst_memberships:
            self._audit_workspace_and_account(workspace, membership.account)
            try:
                auth_domain_membership.remove(membership.account)
            except ValueError:
                # This is fine - this happens if the account is not in the auth domain.
                pass

        # Loop over remaining accounts in the auth domain.
        for account in auth_domain_membership:
            self.errors.append(
                RemoveAccess(
                    collaborative_analysis_workspace=workspace,
                    member=account,
                    note=self.NOT_IN_ANALYST_GROUP,
                )
            )

        # Check that no groups have access.
        group_memberships = GroupGroupMembership.objects.filter(
            parent_group=workspace.workspace.authorization_domains.first(),
        ).exclude(
            # Ignore cc admins group - it is handled differently because it should have admin privileges.
            child_group__name="PRIMED_CC_ADMINS",
        )
        # CC groups that should have access.
        cc_groups = ManagedGroup.objects.filter(
            name__in=[
                "PRIMED_CC_WRITERS",
                "PRIMED_CC_MEMBERS",
            ]
        )
        for cc_group in cc_groups:
            try:
                group_memberships.get(child_group=cc_group)
            except GroupGroupMembership.DoesNotExist:
                self.needs_action.append(
                    GrantAccess(
                        collaborative_analysis_workspace=workspace,
                        member=cc_group,
                        note=self.DCC_ACCESS,
                    )
                )
            else:
                group_memberships = group_memberships.exclude(child_group=cc_group)
                self.verified.append(
                    VerifiedAccess(
                        collaborative_analysis_workspace=workspace,
                        member=cc_group,
                        note=self.DCC_ACCESS,
                    )
                )
        # Any other groups are an error.
        for membership in group_memberships:
            self.errors.append(
                RemoveAccess(
                    collaborative_analysis_workspace=workspace,
                    member=membership.child_group,
                    note=self.UNEXPECTED_GROUP_ACCESS,
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

        # Check whether access is allowed. Start by assuming yes; set to false if the account should not have access.
        access_allowed = True
        account_groups = account.get_all_groups()
        # Loop over all source workspaces.
        for (
            source_workspace
        ) in collaborative_analysis_workspace.source_workspaces.all():
            # Loop over all auth domains for that source workspace.
            for source_auth_domain in source_workspace.authorization_domains.all():
                # If the user is not in the auth domain, they are not allowed to have access to the collab workspace.
                # If so, break out of the loop - it is not necessary to check membership of the remaining auth domains.
                # Note that this only breaks out of the inner loop.
                # It would be more efficient to break out of the outer loop as well.
                if source_auth_domain not in account_groups:
                    access_allowed = False
                    break
        # Check whether the account is in the auth domain of the collab workspace.
        in_auth_domain = (
            collaborative_analysis_workspace.workspace.authorization_domains.first()
            in account_groups
        )
        # Determine the audit result.
        print(access_allowed)
        print(in_auth_domain)
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

    def run_audit(self):
        """Run the audit on the set of workspaces."""
        for workspace in self.queryset:
            self._audit_workspace(workspace)
        self.completed = True

    def get_verified_table(self):
        """Return a table of verified results."""
        return self.results_table_class(
            [x.get_table_dictionary() for x in self.verified]
        )

    def get_needs_action_table(self):
        """Return a table of results where action is needed."""
        return self.results_table_class(
            [x.get_table_dictionary() for x in self.needs_action]
        )

    def get_errors_table(self):
        """Return a table of audit errors."""
        return self.results_table_class([x.get_table_dictionary() for x in self.errors])
