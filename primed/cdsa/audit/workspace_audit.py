from dataclasses import dataclass

import django_tables2 as tables
from anvil_consortium_manager.models import GroupGroupMembership, ManagedGroup
from django.conf import settings
from django.db.models import QuerySet
from django.urls import reverse

# from . import models
from .. import models


@dataclass
class AccessAuditResult:
    """Base class to hold results for auditing CDSA access for a specific SignedAgreement."""

    workspace: models.CDSAWorkspace
    note: str
    data_affiliate_agreement: models.DataAffiliateAgreement = None
    action: str = None

    def __post_init__(self):
        self.anvil_cdsa_group = ManagedGroup.objects.get(
            name=settings.ANVIL_CDSA_GROUP_NAME
        )

    def __str__(self):
        return f"{self.action} for {self.workspace}"

    def get_action_url(self):
        """The URL that handles the action needed."""
        return reverse(
            "cdsa:workspaces:audit:resolve",
            args=[
                self.workspace.workspace.billing_project.name,
                self.workspace.workspace.name,
            ],
        )

    def get_table_dictionary(self):
        """Return a dictionary that can be used to populate an instance of `SignedAgreementAccessAuditTable`."""
        row = {
            "workspace": self.workspace,
            "data_affiliate_agreement": self.data_affiliate_agreement,
            "note": self.note,
            "action": self.action,
            "action_url": self.get_action_url(),
        }
        return row


@dataclass
class VerifiedAccess(AccessAuditResult):
    """Audit results class for when access has been verified."""

    def __str__(self):
        return f"Verified access: {self.note}"


@dataclass
class VerifiedNoAccess(AccessAuditResult):
    """Audit results class for when no access has been verified."""

    def __str__(self):
        return f"Verified no access: {self.note}"


@dataclass
class GrantAccess(AccessAuditResult):
    """Audit results class for when access should be granted."""

    action: str = "Grant access"

    def __str__(self):
        return f"Grant access: {self.note}"


@dataclass
class RemoveAccess(AccessAuditResult):
    """Audit results class for when access should be removed for a known reason."""

    action: str = "Remove access"

    def __str__(self):
        return f"Remove access: {self.note}"


@dataclass
class OtherError(AccessAuditResult):
    """Audit results class for when an error has been detected (e.g., has access and never should have)."""

    pass


class WorkspaceAccessAuditTable(tables.Table):
    """A table to show results from a WorkspaceAccessAudit instance."""

    workspace = tables.Column(linkify=True)
    data_affiliate_agreement = tables.Column(linkify=True)
    agreement_version = tables.Column(
        accessor="data_affiliate_agreement__signed_agreement__version"
    )
    note = tables.Column()
    action = tables.TemplateColumn(
        template_name="cdsa/snippets/cdsa_workspace_audit_action_button.html"
    )

    class Meta:
        attrs = {"class": "table align-middle"}


class WorkspaceAccessAudit:
    """Audit for CDSA Workspaces."""

    # Access verified.
    ACTIVE_PRIMARY_AGREEMENT = "Active primary CDSA."

    # Allowed reasons for no access.
    NO_PRIMARY_AGREEMENT = "No primary CDSA for this study."
    INACTIVE_PRIMARY_AGREEMENT = "Primary CDSA for this study is inactive."

    # Other errors
    ERROR_OTHER_CASE = "Workspace did not match any expected situations."

    results_table_class = WorkspaceAccessAuditTable

    def __init__(self, cdsa_workspace_queryset=None):
        # Store the CDSA group for auditing membership.
        self.anvil_cdsa_group = ManagedGroup.objects.get(
            name=settings.ANVIL_CDSA_GROUP_NAME
        )
        self.completed = False
        # Set up lists to hold audit results.
        self.verified = []
        self.needs_action = []
        self.errors = []
        # Store the queryset to run the audit on.
        if cdsa_workspace_queryset is None:
            cdsa_workspace_queryset = models.CDSAWorkspace.objects.all()
        if not (
            isinstance(cdsa_workspace_queryset, QuerySet)
            and cdsa_workspace_queryset.model is models.CDSAWorkspace
        ):
            raise ValueError(
                "cdsa_workspace_queryset must be a queryset of CDSAWorkspace objects."
            )
        self.cdsa_workspace_queryset = cdsa_workspace_queryset

    def _audit_workspace(self, workspace):
        # Check if the access group is in the overall CDSA group.
        auth_domain = workspace.workspace.authorization_domains.first()
        has_cdsa_group_in_auth_domain = GroupGroupMembership.objects.filter(
            parent_group=auth_domain,
            child_group=self.anvil_cdsa_group,
        ).exists()
        primary_qs = models.DataAffiliateAgreement.objects.filter(
            study=workspace.study, signed_agreement__is_primary=True
        )
        primary_exists = primary_qs.exists()

        if primary_exists:
            primary_agreement = (
                primary_qs.filter(
                    signed_agreement__status=models.SignedAgreement.StatusChoices.ACTIVE,
                )
                .order_by(
                    "-signed_agreement__version__major_version__version",
                    "-signed_agreement__version__minor_version",
                )
                .first()
            )
            if primary_agreement:
                if has_cdsa_group_in_auth_domain:
                    self.verified.append(
                        VerifiedAccess(
                            workspace=workspace,
                            data_affiliate_agreement=primary_agreement,
                            note=self.ACTIVE_PRIMARY_AGREEMENT,
                        )
                    )
                    return
                else:
                    self.needs_action.append(
                        GrantAccess(
                            workspace=workspace,
                            data_affiliate_agreement=primary_agreement,
                            note=self.ACTIVE_PRIMARY_AGREEMENT,
                        )
                    )
                    return
            else:
                if has_cdsa_group_in_auth_domain:
                    self.needs_action.append(
                        RemoveAccess(
                            workspace=workspace,
                            data_affiliate_agreement=primary_agreement,
                            note=self.INACTIVE_PRIMARY_AGREEMENT,
                        )
                    )
                    return
                else:
                    self.verified.append(
                        VerifiedNoAccess(
                            workspace=workspace,
                            data_affiliate_agreement=primary_agreement,
                            note=self.INACTIVE_PRIMARY_AGREEMENT,
                        )
                    )
                    return
        else:
            if has_cdsa_group_in_auth_domain:
                self.errors.append(
                    RemoveAccess(
                        workspace=workspace,
                        data_affiliate_agreement=None,
                        note=self.NO_PRIMARY_AGREEMENT,
                    )
                )
                return
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        workspace=workspace,
                        data_affiliate_agreement=None,
                        note=self.NO_PRIMARY_AGREEMENT,
                    )
                )
                return

    def run_audit(self):
        """Run an audit on all SignedAgreements."""
        for workspace in self.cdsa_workspace_queryset:
            self._audit_workspace(workspace)
        self.completed = True

    def get_verified_table(self):
        """Return a table of verified results."""
        return self.results_table_class(
            [x.get_table_dictionary() for x in self.verified]
        )

    def get_all_results(self):
        return self.verified + self.needs_action + self.errors

    def get_needs_action_table(self):
        """Return a table of results where action is needed."""
        return self.results_table_class(
            [x.get_table_dictionary() for x in self.needs_action]
        )

    def get_errors_table(self):
        """Return a table of audit errors."""
        return self.results_table_class([x.get_table_dictionary() for x in self.errors])
