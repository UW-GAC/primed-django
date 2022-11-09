from dataclasses import dataclass

import django_tables2 as tables
from django.urls import reverse
from django.utils.safestring import mark_safe

# from . import models
from .models import dbGaPDataAccessRequest, dbGaPWorkspace


# Dataclasses for storing audit results?
@dataclass
class AuditResult:
    workspace: dbGaPWorkspace
    note: str
    data_access_request: dbGaPDataAccessRequest = None

    def get_action_url(self):
        return None

    def get_action(self):
        return None

    def get_table_dictionary(self):
        row = {
            "workspace": self.workspace,
            "data_access_request": self.data_access_request,
            "note": self.note,
            "action": self.get_action(),
            "action_url": self.get_action_url(),
        }
        return row


@dataclass
class VerifiedAccess(AuditResult):
    pass


@dataclass
class VerifiedNoAccess(AuditResult):
    pass


@dataclass
class GrantAccess(AuditResult):
    def get_action_url(self):
        return reverse(
            "anvil_consortium_manager:managed_groups:member_groups:new_by_child",
            args=[
                self.workspace.workspace.authorization_domains.first(),
                self.data_access_request.dbgap_data_access_snapshot.dbgap_application.anvil_group,
            ],
        )

    def get_action(self):
        return "Grant access"


@dataclass
class RemoveAccess(AuditResult):
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
    pass


class dbGaPDataAccessSnapshotAudit:

    # Access verified.
    APPROVED_DAR = "Approved DAR."

    # Allowed reasons for no access.
    NO_DAR = "No matching DAR."
    DAR_NOT_APPROVED = "DAR is not approved."

    # Allowed reasons to grant or remove access.
    NEW_APPROVED_DAR = "New approved DAR."
    NEW_WORKSPACE = "New workspace."
    PREVIOUS_APPROVAL = "Previously approved."

    # Unexpected.
    ERROR_HAS_ACCESS = "Has access for an unknown reason."

    def __init__(self, dbgap_data_access_snapshot):
        self.snapshot = dbgap_data_access_snapshot
        self.completed = False
        # Set up lists to hold audit results.
        self.verified = None
        self.needs_action = None
        self.errors = None

    def run_audit(self):
        self.verified = []
        self.needs_action = []
        self.errors = []

        # Get a list of all dbGaP workspaces.
        dbgap_workspaces = dbGaPWorkspace.objects.all()
        # Loop through workspaces and verify access.
        for dbgap_workspace in dbgap_workspaces:
            self._audit_workspace(dbgap_workspace)
        self.completed = True

    def _audit_workspace(self, dbgap_workspace):
        """Audit access for a specific dbGaPWorkspace."""
        try:
            # There should only be one DAR from this snapshot associated with a given workspace.
            dar = dbgap_workspace.get_data_access_requests().get(
                dbgap_data_access_snapshot=self.snapshot
            )
        except dbGaPDataAccessRequest.DoesNotExist:
            # No matching DAR exists for this snapshot.
            # Check if the group is in the auth domain.
            has_access = dbgap_workspace.workspace.is_in_authorization_domain(
                self.snapshot.dbgap_application.anvil_group
            )
            if has_access:
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
        # If we found a matching DAR, proceed with additional checks.
        in_auth_domain = dbgap_workspace.workspace.is_in_authorization_domain(
            self.snapshot.dbgap_application.anvil_group
        )
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
        return dbGaPDataAccessSnapshotAuditTable(
            [x.get_table_dictionary() for x in self.verified]
        )

    def get_needs_action_table(self):
        return dbGaPDataAccessSnapshotAuditTable(
            [x.get_table_dictionary() for x in self.needs_action]
        )

    def get_errors_table(self):
        return dbGaPDataAccessSnapshotAuditTable(
            [x.get_table_dictionary() for x in self.errors]
        )


class dbGaPDataAccessSnapshotAuditTable(tables.Table):
    """A table to show results from a dbGaPDataAccessSnapshotAudit."""

    workspace = tables.Column(linkify=True)
    data_access_request = tables.Column()
    note = tables.Column()
    action = tables.Column()

    def render_action(self, record, value):
        return mark_safe(
            """<a href="{}" class="btn btn-primary">{}</a>""".format(
                record["action_url"], value
            )
        )
