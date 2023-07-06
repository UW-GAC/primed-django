from dataclasses import dataclass

import django_tables2 as tables
from anvil_consortium_manager.models import GroupGroupMembership, ManagedGroup
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe

# from . import models
from .. import models


@dataclass
class AccessAuditResult:
    """Base class to hold results for auditing CDSA access for a specific SignedAgreement."""

    workspace: models.CDSAWorkspace
    note: str
    data_affiliate_agreement: models.DataAffiliateAgreement = None

    # def __init__(self, *args, **kwargs):
    #     super().__init(*args, **kwargs)
    #     self.anvil_cdsa_group = ManagedGroup.objects.get(name="PRIMED_CDSA")

    def __post_init__(self):
        self.anvil_cdsa_group = ManagedGroup.objects.get(
            name=settings.ANVIL_CDSA_GROUP_NAME
        )

    def get_action_url(self):
        """The URL that handles the action needed."""
        return None

    def get_action(self):
        """An indicator of what action needs to be taken."""
        return None

    def get_table_dictionary(self):
        """Return a dictionary that can be used to populate an instance of `SignedAgreementAccessAuditTable`."""
        row = {
            "workspace": self.workspace,
            "data_affiliate_agreement": self.data_affiliate_agreement,
            "note": self.note,
            "action": self.get_action(),
            "action_url": self.get_action_url(),
        }
        return row


@dataclass
class VerifiedAccess(AccessAuditResult):
    """Audit results class for when access has been verified."""

    pass


@dataclass
class VerifiedNoAccess(AccessAuditResult):
    """Audit results class for when no access has been verified."""

    pass


@dataclass
class GrantAccess(AccessAuditResult):
    """Audit results class for when access should be granted."""

    def get_action(self):
        return "Grant access"

    def get_action_url(self):
        return reverse(
            "anvil_consortium_manager:managed_groups:member_groups:new_by_child",
            args=[
                self.workspace.workspace.authorization_domains.first(),
                self.anvil_cdsa_group,
            ],
        )


@dataclass
class RemoveAccess(AccessAuditResult):
    """Audit results class for when access should be removed for a known reason."""

    def get_action(self):
        return "Remove access"

    def get_action_url(self):
        return reverse(
            "anvil_consortium_manager:managed_groups:member_groups:delete",
            args=[
                self.workspace.workspace.authorization_domains.first(),
                self.anvil_cdsa_group,
            ],
        )


@dataclass
class OtherError(AccessAuditResult):
    """Audit results class for when an error has been detected (e.g., has access and never should have)."""

    pass


class WorkspaceAccessAuditTable(tables.Table):
    """A table to show results from a WorkspaceAccessAudit instance."""

    workspace = tables.Column(linkify=True)
    data_affiliate_agreement = tables.Column(linkify=True)
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


class WorkspaceAccessAudit:
    """Audit for CDSA Workspaces."""

    # Access verified.
    VALID_PRIMARY_CDSA = "Valid primary CDSA."

    # Allowed reasons for no access.
    NO_PRIMARY_CDSA = "No primary CDSA for this study exists."

    # Other errors
    ERROR_OTHER_CASE = "Workspace did not match any expected situations."

    results_table_class = WorkspaceAccessAuditTable

    def __init__(self):
        # Store the CDSA group for auditing membership.
        self.anvil_cdsa_group = ManagedGroup.objects.get(
            name=settings.ANVIL_CDSA_GROUP_NAME
        )
        self.completed = False
        # Set up lists to hold audit results.
        self.verified = []
        self.needs_action = []
        self.errors = []

    # Audit a single signed agreement.
    def _audit_workspace(self, workspace):
        # Check if the access group is in the overall CDSA group.
        auth_domain = workspace.workspace.authorization_domains.first()
        has_cdsa_group_in_auth_domain = GroupGroupMembership.objects.filter(
            parent_group=auth_domain,
            child_group=self.anvil_cdsa_group,
        ).exists()
        # WRITE ME!
        # See if there is a primary data affiliate agreement for this study.
        try:
            primary_agreement = models.DataAffiliateAgreement.objects.get(
                study=workspace.study,
                signed_agreement__is_primary=True,
            )
            if has_cdsa_group_in_auth_domain:
                self.verified.append(
                    VerifiedAccess(
                        workspace=workspace,
                        data_affiliate_agreement=primary_agreement,
                        note=self.VALID_PRIMARY_CDSA,
                    )
                )
                return
            else:
                self.needs_action.append(
                    GrantAccess(
                        workspace=workspace,
                        data_affiliate_agreement=primary_agreement,
                        note=self.VALID_PRIMARY_CDSA,
                    )
                )
                return
        except models.DataAffiliateAgreement.DoesNotExist:
            if not has_cdsa_group_in_auth_domain:
                self.verified.append(
                    VerifiedNoAccess(
                        workspace=workspace,
                        data_affiliate_agreement=None,
                        note=self.NO_PRIMARY_CDSA,
                    )
                )
                return
            else:
                self.errors.append(
                    RemoveAccess(
                        workspace=workspace,
                        data_affiliate_agreement=None,
                        note=self.NO_PRIMARY_CDSA,
                    )
                )
                return

    def run_audit(self):
        """Run an audit on all SignedAgreements."""
        for workspace in models.CDSAWorkspace.objects.all():
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
