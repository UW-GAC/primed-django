from dataclasses import dataclass

from anvil_consortium_manager.models import Account
from django.urls import reverse

from . import models


@dataclass
class AccessAuditResult:
    """Base class to hold the result of an access audit for a CollaborativeAnalysisWorkspace."""

    workspace: models.CollaborativeAnalysisWorkspace
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
                self.workspace.workspace.authorization_domains.first(),
                self.account,
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
                self.workspace.workspace.authorization_domains.first(),
                self.account,
            ],
        )
