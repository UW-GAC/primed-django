from dataclasses import dataclass

from anvil_consortium_manager.models import Account
from django.urls import reverse

from . import models


@dataclass
class AccessAuditResult:
    """Base class to hold the result of an access audit for a CollaborativeAnalysisWorkspace."""

    collaborative_analysis_workspace: models.CollaborativeAnalysisWorkspace
    account: Account
    note: str

    def get_action_url(self):
        """The URL that handles the action needed."""
        return None

    def get_action(self):
        """An indicator of what action needs to be taken."""
        return None


@dataclass
class VerifiedAccess(AccessAuditResult):
    """Audit results class for when an account has verified access."""


@dataclass
class VerifiedNoAccess(AccessAuditResult):
    """Audit results class for when an account has verified no access."""


@dataclass
class GrantAccess(AccessAuditResult):
    """Audit results class for when an account should be granted access."""

    def get_action(self):
        return "Grant access"

    def get_action_url(self):
        return reverse(
            "anvil_consortium_manager:managed_groups:member_accounts:new_by_account",
            args=[
                self.collaborative_analysis_workspace.workspace.authorization_domains.first().name,
                self.account.uuid,
            ],
        )


@dataclass
class RemoveAccess(AccessAuditResult):
    """Audit results class for when access for an account should be removed."""

    def get_action(self):
        return "Remove access"

    def get_action_url(self):
        return reverse(
            "anvil_consortium_manager:managed_groups:member_accounts:delete",
            args=[
                self.collaborative_analysis_workspace.workspace.authorization_domains.first().name,
                self.account.uuid,
            ],
        )


class CollaborativeAnalysisWorkspaceAccessAudit:
    """Class to audit access to a CollaborativeAnalysisWorkspace."""

    # Allowed reasons for access.
    IN_SOURCE_AUTH_DOMAINS = "Account is in all source auth domains for this workspace."

    # Allowed reasons for no access.
    NOT_IN_SOURCE_AUTH_DOMAINS = (
        "Account is not in all source auth domains for this workspace."
    )

    def __init__(self):
        self.verified = []
        self.needs_action = []
        self.errors = []
        self.completed = False

    def _audit_workspace(self, workspace):
        """Audit access to a single CollaborativeAnalysisWorkspace."""
        pass

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
                    account=account,
                    note=self.IN_SOURCE_AUTH_DOMAINS,
                )
            )
        elif access_allowed and not in_auth_domain:
            self.needs_action.append(
                GrantAccess(
                    collaborative_analysis_workspace=collaborative_analysis_workspace,
                    account=account,
                    note=self.IN_SOURCE_AUTH_DOMAINS,
                )
            )
        elif not access_allowed and in_auth_domain:
            self.needs_action.append(
                RemoveAccess(
                    collaborative_analysis_workspace=collaborative_analysis_workspace,
                    account=account,
                    note=self.NOT_IN_SOURCE_AUTH_DOMAINS,
                )
            )
        else:
            self.verified.append(
                VerifiedNoAccess(
                    collaborative_analysis_workspace=collaborative_analysis_workspace,
                    account=account,
                    note=self.NOT_IN_SOURCE_AUTH_DOMAINS,
                )
            )

    def run_audit(self):
        """Run an audit on all CollaborativeAnalysisWorkspaces."""
        for workspace in models.CollaborativeAnalysisWorkspace.objects.all():
            self._audit_workspace(workspace)
        self.completed = True
