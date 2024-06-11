from dataclasses import dataclass
from typing import Union

import django_tables2 as tables
from anvil_consortium_manager import Account, ManagedGroup
from django.urls import reverse

from primed.primed_anvil.audit import PRIMEDAudit, PRIMEDAuditResult
from primed.primed_anvil.tables import BooleanIconColumn

from ..models import dbGaPApplication


@dataclass
class AuditResult(PRIMEDAuditResult):
    """Base class to hold results for auditing collaborators for a dbGaP application."""

    dbgap_application: dbGaPApplication
    member: Union[Account, ManagedGroup]
    has_access: bool
    note: str
    action: str = None

    def get_action_url(self):
        """The URL that handles the action needed."""
        return reverse(
            "dbgap:audit:collaborators:resolve",
            args=[
                self.dbgap_application.dbgap_project_id,
                self.member.email,
            ],
        )

    def get_table_dictionary(self):
        """Return a dictionary that can be used to populate an instance of `dbGaPDataAccessSnapshotAuditTable`."""
        row = {
            "application": self.dbgap_application,
            "member": self.member,
            "has_access": self.has_access,
            "note": self.note,
            "action": self.action,
            "action_url": self.get_action_url(),
        }
        return row


# @dataclass
# class VerifiedAccess(AuditResult):
#     """Audit results class for when access has been verified."""

#     has_access: bool = True

#     def __str__(self):
#         return f"Verified access: {self.note}"


# @dataclass
# class VerifiedNoAccess(AuditResult):
#     """Audit results class for when no access has been verified."""

#     has_access: bool = False

#     def __str__(self):
#         return f"Verified no access: {self.note}"


# @dataclass
# class GrantAccess(AuditResult):
#     """Audit results class for when access should be granted."""

#     has_access: bool = False
#     action: str = "Grant access"

#     def __str__(self):
#         return f"Grant access: {self.note}"


# @dataclass
# class RemoveAccess(AuditResult):
#     """Audit results class for when access should be removed for a known reason."""

#     has_access: bool = True
#     action: str = "Remove access"

#     def __str__(self):
#         return f"Remove access: {self.note}"


# @dataclass
# class Error(AuditResult):
#     """Audit results class for when an error has been detected (e.g., has access and never should have)."""

#     pass


class dbGaPCollaboratorAuditTable(tables.Table):
    """A table to show results from a dbGaPCollaboratorAudit subclass."""

    application = tables.Column(linkify=True)
    member = tables.Column(linkify=True)
    has_access = BooleanIconColumn(show_false_icon=True)
    note = tables.Column()
    action = tables.TemplateColumn(template_name="dbgap/snippets/dbgap_audit_action_button.html")

    class Meta:
        attrs = {"class": "table align-middle"}


class dbGaPCollaboratorAudit(PRIMEDAudit):
    pass
    # # Access verified.
    # APPROVED_DAR = "Approved DAR."

    # # Allowed reasons for no access.
    # NO_SNAPSHOTS = "No snapshots for this application."
    # NO_DAR = "No matching DAR."
    # DAR_NOT_APPROVED = "DAR is not approved."

    # # Allowed reasons to grant or remove access.
    # NEW_APPROVED_DAR = "New approved DAR."
    # NEW_WORKSPACE = "New workspace."
    # PREVIOUS_APPROVAL = "Previously approved."

    # # Unexpected.
    # ERROR_HAS_ACCESS = "Has access for an unknown reason."

    # results_table_class = dbGaPAccessAuditTable

    # def __init__(self, dbgap_application_queryset=None, dbgap_workspace_queryset=None):
    #     super().__init__()
    #     if dbgap_application_queryset is None:
    #         dbgap_application_queryset = dbGaPApplication.objects.all()
    #     if not (
    #         isinstance(dbgap_application_queryset, QuerySet) and dbgap_application_queryset.model is dbGaPApplication
    #     ):
    #         raise ValueError("dbgap_application_queryset must be a queryset of dbGaPApplication objects.")
    #     self.dbgap_application_queryset = dbgap_application_queryset
    #     if dbgap_workspace_queryset is None:
    #         dbgap_workspace_queryset = dbGaPWorkspace.objects.all()
    #     if not (isinstance(dbgap_workspace_queryset, QuerySet) and dbgap_workspace_queryset.model is dbGaPWorkspace):
    #         raise ValueError("dbgap_workspace_queryset must be a queryset of dbGaPWorkspace objects.")
    #     self.dbgap_workspace_queryset = dbgap_workspace_queryset

    # def _run_audit(self):
    #     for dbgap_application in self.dbgap_application_queryset:
    #         for dbgap_workspace in self.dbgap_workspace_queryset:
    #             self.audit_application_and_workspace(dbgap_application, dbgap_workspace)

    # def audit_application_and_workspace(self, dbgap_application, dbgap_workspace):
    #     """Audit access for a specific dbGaP application and a specific workspace."""
    #     in_auth_domain = dbgap_workspace.workspace.is_in_authorization_domain(dbgap_application.anvil_access_group)

    #     # Get the most recent snapshot.
    #     try:
    #         dar_snapshot = dbgap_application.dbgapdataaccesssnapshot_set.get(is_most_recent=True)
    #     except dbGaPDataAccessSnapshot.DoesNotExist:
    #         if in_auth_domain:
    #             # Error!
    #             self.errors.append(
    #                 RemoveAccess(
    #                     workspace=dbgap_workspace,
    #                     dbgap_application=dbgap_application,
    #                     data_access_request=None,
    #                     note=self.ERROR_HAS_ACCESS,
    #                 )
    #             )
    #         else:
    #             # As expected, no access and no DAR
    #             self.verified.append(
    #                 VerifiedNoAccess(
    #                     workspace=dbgap_workspace,
    #                     dbgap_application=dbgap_application,
    #                     note=self.NO_SNAPSHOTS,
    #                 )
    #             )
    #         return  # Go to the next workspace.

    #     try:
    #         # There should only be one DAR from this snapshot associated with a given workspace.
    #         dar = dbgap_workspace.get_data_access_requests().get(dbgap_data_access_snapshot=dar_snapshot)
    #     except dbGaPDataAccessRequest.DoesNotExist:
    #         # No matching DAR exists for this application.
    #         if in_auth_domain:
    #             # Error!
    #             self.errors.append(
    #                 RemoveAccess(
    #                     workspace=dbgap_workspace,
    #                     dbgap_application=dbgap_application,
    #                     data_access_request=None,
    #                     note=self.ERROR_HAS_ACCESS,
    #                 )
    #             )
    #         else:
    #             # As expected, no access and no DAR
    #             self.verified.append(
    #                 VerifiedNoAccess(
    #                     workspace=dbgap_workspace,
    #                     dbgap_application=dbgap_application,
    #                     note=self.NO_DAR,
    #                 )
    #             )
    #         return  # Go to the next workspace.

    #     # Is the dbGaP access group associated with the DAR in the auth domain of the workspace?
    #     # We'll need to know this for future checks.
    #     if dar.is_approved and in_auth_domain:
    #         # Verified access!
    #         self.verified.append(
    #             VerifiedAccess(
    #                 workspace=dbgap_workspace,
    #                 dbgap_application=dbgap_application,
    #                 data_access_request=dar,
    #                 note=self.APPROVED_DAR,
    #             )
    #         )
    #     elif dar.is_approved and not in_auth_domain:
    #         # Check why we should grant access.
    #         # Do we need to differentiate between NEW and UPDATED dars? I don't think so.
    #         if dbgap_workspace.created > dar.dbgap_data_access_snapshot.created:
    #             self.needs_action.append(
    #                 GrantAccess(
    #                     workspace=dbgap_workspace,
    #                     dbgap_application=dbgap_application,
    #                     data_access_request=dar,
    #                     note=self.NEW_WORKSPACE,
    #                 )
    #             )
    #         else:
    #             self.needs_action.append(
    #                 GrantAccess(
    #                     workspace=dbgap_workspace,
    #                     dbgap_application=dbgap_application,
    #                     data_access_request=dar,
    #                     note=self.NEW_APPROVED_DAR,
    #                 )
    #             )
    #     elif not dar.is_approved and in_auth_domain:
    #         # Group has access that needs to be removed.
    #         # Make sure it is due to an expected reason. So far, the only reason is because the DAR was approved
    #         # during the last snapshot, and it no longer is.
    #         # Check if this dbgap_dar_id was ever approved in the past.
    #         previously_approved = (
    #             dbGaPDataAccessRequest.objects.approved()
    #             .filter(
    #                 dbgap_dar_id=dar.dbgap_dar_id,
    #                 dbgap_data_access_snapshot__created__lt=dar.dbgap_data_access_snapshot.created,
    #             )
    #             .exists()
    #         )
    #         if previously_approved:
    #             self.needs_action.append(
    #                 RemoveAccess(
    #                     workspace=dbgap_workspace,
    #                     dbgap_application=dbgap_application,
    #                     data_access_request=dar,
    #                     note=self.PREVIOUS_APPROVAL,
    #                 )
    #             )
    #         else:
    #             # Otherwise, it's an error.
    #             self.errors.append(
    #                 RemoveAccess(
    #                     workspace=dbgap_workspace,
    #                     dbgap_application=dbgap_application,
    #                     data_access_request=dar,
    #                     note=self.ERROR_HAS_ACCESS,
    #                 )
    #             )
    #         pass
    #     else:
    #         # Verified no access because DAR is not approved.
    #         self.verified.append(
    #             VerifiedNoAccess(
    #                 workspace=dbgap_workspace,
    #                 dbgap_application=dbgap_application,
    #                 data_access_request=dar,
    #                 note=self.DAR_NOT_APPROVED,
    #             )
    #         )
