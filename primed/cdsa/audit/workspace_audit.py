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
    agreement_version = tables.Column(
        accessor="data_affiliate_agreement__signed_agreement__version"
    )
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
    ACTIVE_PRIMARY_AGREEMENT = "Active primary CDSA."

    # Allowed reasons for no access.
    NO_PRIMARY_AGREEMENT = "No primary CDSA for this study."
    INACTIVE_PRIMARY_AGREEMENT = "Primary CDSA for this study is inactive."

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
