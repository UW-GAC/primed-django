from dataclasses import dataclass

# from . import models
from .models import dbGaPDataAccessRequest, dbGaPWorkspace


# Dataclasses for storing audit results?
@dataclass
class AuditResult:
    workspace: dbGaPWorkspace


@dataclass
class VerifiedAccess(AuditResult):
    data_access_request: dbGaPDataAccessRequest


@dataclass
class VerifiedNoAccess(AuditResult):
    note: str
    data_access_request: dbGaPDataAccessRequest = None


@dataclass
class GrantAccess(AuditResult):
    data_access_request: dbGaPDataAccessRequest
    note: str


@dataclass
class RemoveAccess(AuditResult):
    data_access_request: dbGaPDataAccessRequest
    note: str


@dataclass
class Error(AuditResult):
    note: str
    data_access_request: dbGaPDataAccessRequest = None


class dbGaPDataAccessSnapshotAudit:

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
                VerifiedAccess(workspace=dbgap_workspace, data_access_request=dar)
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
