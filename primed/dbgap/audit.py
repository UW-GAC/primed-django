from abc import ABC
from dataclasses import dataclass

import django_tables2 as tables
from django.urls import reverse
from django.utils.safestring import mark_safe

# from . import models
from .models import dbGaPDataAccessRequest, dbGaPDataAccessSnapshot, dbGaPWorkspace


# Dataclasses for storing audit results?
@dataclass
class AuditResult:
    """Base class to hold results for auditing dbGaP workspace access for a dbGaPDataAccessSnapshot."""

    workspace: dbGaPWorkspace
    note: str
    data_access_request: dbGaPDataAccessRequest = None

    def get_action_url(self):
        """The URL that handles the action needed."""
        return None

    def get_action(self):
        """An indicator of what action needs to be taken."""
        return None

    def get_table_dictionary(self):
        """Return a dictionary that can be used to populate an instance of `dbGaPDataAccessSnapshotAuditTable`."""
        if self.data_access_request:
            dar_accession = self.data_access_request.get_dbgap_accession()
            dar_consent = self.data_access_request.dbgap_consent_abbreviation
        else:
            dar_accession = None
            dar_consent = None
        row = {
            "workspace": self.workspace,
            "data_access_request": self.data_access_request,
            "dar_accession": dar_accession,
            "dar_consent": dar_consent,
            "note": self.note,
            "action": self.get_action(),
            "action_url": self.get_action_url(),
        }
        return row


@dataclass
class VerifiedAccess(AuditResult):
    """Audit results class for when access has been verified."""

    pass


@dataclass
class VerifiedNoAccess(AuditResult):
    """Audit results class for when no access has been verified."""

    pass


@dataclass
class GrantAccess(AuditResult):
    """Audit results class for when access should be granted."""

    def get_action(self):
        return "Grant access"

    def get_action_url(self):
        return reverse(
            "anvil_consortium_manager:managed_groups:member_groups:new_by_child",
            args=[
                self.workspace.workspace.authorization_domains.first(),
                self.data_access_request.dbgap_data_access_snapshot.dbgap_application.anvil_group,
            ],
        )


@dataclass
class RemoveAccess(AuditResult):
    """Audit results class for when access should be removed for a known reason."""

    def get_action(self):
        return "Remove access"

    def get_action_url(self):
        return reverse(
            "anvil_consortium_manager:managed_groups:member_groups:delete",
            args=[
                self.workspace.workspace.authorization_domains.first(),
                self.data_access_request.dbgap_data_access_snapshot.dbgap_application.anvil_group,
            ],
        )


@dataclass
class Error(AuditResult):
    """Audit results class for when an error has been detected (e.g., has access and never should have)."""

    pass


class dbGaPAccessAuditTable(tables.Table):
    """A table to show results from a dbGaPAccessAudit subclass."""

    workspace = tables.Column(linkify=True)
    data_access_request = tables.Column()
    dar_accession = tables.Column(verbose_name="DAR accession")
    dar_consent = tables.Column(verbose_name="DAR consent")
    note = tables.Column()
    action = tables.Column()

    def render_action(self, record, value):
        return mark_safe(
            """<a href="{}" class="btn btn-primary">{}</a>""".format(
                record["action_url"], value
            )
        )


class dbGaPAccessAudit(ABC):

    # Access verified.
    APPROVED_DAR = "Approved DAR."

    # Allowed reasons for no access.
    NO_SNAPSHOTS = "No snapshots for this application."
    NO_DAR = "No matching DAR."
    DAR_NOT_APPROVED = "DAR is not approved."

    # Allowed reasons to grant or remove access.
    NEW_APPROVED_DAR = "New approved DAR."
    NEW_WORKSPACE = "New workspace."
    PREVIOUS_APPROVAL = "Previously approved."

    # Unexpected.
    ERROR_HAS_ACCESS = "Has access for an unknown reason."

    results_table_class = dbGaPAccessAuditTable

    def __init__(self):
        self.completed = False
        # Set up lists to hold audit results.
        self.verified = None
        self.needs_action = None
        self.errors = None

    def audit_application_and_workspace(self, dbgap_application, dbgap_workspace):
        """Audit access for a specific dbGaP application and a specific workspace."""
        in_auth_domain = dbgap_workspace.workspace.is_in_authorization_domain(
            dbgap_application.anvil_group
        )

        # Get the most recent snapshot.
        try:
            dar_snapshot = dbgap_application.dbgapdataaccesssnapshot_set.get(
                is_most_recent=True
            )
        except dbGaPDataAccessSnapshot.DoesNotExist:
            if in_auth_domain:
                # Error!
                self.errors.append(
                    RemoveAccess(
                        workspace=dbgap_workspace,
                        data_access_request=None,
                        note=self.ERROR_HAS_ACCESS,
                    )
                )
            else:
                # As expected, no access and no DAR
                self.verified.append(
                    VerifiedNoAccess(workspace=dbgap_workspace, note=self.NO_SNAPSHOTS)
                )
            return  # Go to the next workspace.

        try:
            # There should only be one DAR from this snapshot associated with a given workspace.
            dar = dbgap_workspace.get_data_access_requests().get(
                dbgap_data_access_snapshot=dar_snapshot
            )
        except dbGaPDataAccessRequest.DoesNotExist:
            # No matching DAR exists for this application.
            if in_auth_domain:
                # Error!
                self.errors.append(
                    RemoveAccess(
                        workspace=dbgap_workspace,
                        data_access_request=None,
                        note=self.ERROR_HAS_ACCESS,
                    )
                )
            else:
                # As expected, no access and no DAR
                self.verified.append(
                    VerifiedNoAccess(workspace=dbgap_workspace, note=self.NO_DAR)
                )
            return  # Go to the next workspace.

        # Is the dbGaP access group associated with the DAR in the auth domain of the workspace?
        # We'll need to know this for future checks.
        if dar.is_approved and in_auth_domain:
            # Verified access!
            self.verified.append(
                VerifiedAccess(
                    workspace=dbgap_workspace,
                    data_access_request=dar,
                    note=self.APPROVED_DAR,
                )
            )
        elif dar.is_approved and not in_auth_domain:
            # Check why we should grant access.
            # Do we need to differentiate between NEW and UPDATED dars? I don't think so.
            if dbgap_workspace.created > dar.dbgap_data_access_snapshot.created:
                self.needs_action.append(
                    GrantAccess(
                        workspace=dbgap_workspace,
                        data_access_request=dar,
                        note=self.NEW_WORKSPACE,
                    )
                )
            else:
                self.needs_action.append(
                    GrantAccess(
                        workspace=dbgap_workspace,
                        data_access_request=dar,
                        note=self.NEW_APPROVED_DAR,
                    )
                )
        elif not dar.is_approved and in_auth_domain:
            # Group has access that needs to be removed.
            # Make sure it is due to an expected reason. So far, the only reason is because the DAR was approved during
            # the last snapshot, and it no longer is.
            # Check if this dbgap_dar_id was ever approved in the past.
            previously_approved = (
                dbGaPDataAccessRequest.objects.approved()
                .filter(
                    dbgap_dar_id=dar.dbgap_dar_id,
                    dbgap_data_access_snapshot__created__lt=dar.dbgap_data_access_snapshot.created,
                )
                .exists()
            )
            if previously_approved:
                self.needs_action.append(
                    RemoveAccess(
                        workspace=dbgap_workspace,
                        data_access_request=dar,
                        note=self.PREVIOUS_APPROVAL,
                    )
                )
            else:
                # Otherwise, it's an error.
                self.errors.append(
                    RemoveAccess(
                        workspace=dbgap_workspace,
                        data_access_request=dar,
                        note=self.ERROR_HAS_ACCESS,
                    )
                )
            pass
        else:
            # Verified no access because DAR is not approved.
            self.verified.append(
                VerifiedNoAccess(
                    workspace=dbgap_workspace,
                    data_access_request=dar,
                    note=self.DAR_NOT_APPROVED,
                )
            )

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


class dbGaPApplicationAccessAudit(dbGaPAccessAudit):
    def __init__(self, dbgap_application):
        super().__init__()
        self.dbgap_application = dbgap_application

    def run_audit(self):
        """Audit all workspaces against access provided by this dbGaPApplication."""
        self.verified = []
        self.needs_action = []
        self.errors = []

        # Get a list of all dbGaP workspaces.
        dbgap_workspaces = dbGaPWorkspace.objects.all()
        # Loop through workspaces and verify access.
        for dbgap_workspace in dbgap_workspaces:
            self.audit_application_and_workspace(
                self.dbgap_application, dbgap_workspace
            )
        self.completed = True
