from dataclasses import dataclass
from typing import Union

import django_tables2 as tables
from anvil_consortium_manager.models import Account, GroupAccountMembership, GroupGroupMembership, ManagedGroup
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet
from django.urls import reverse

from primed.primed_anvil.audit import PRIMEDAudit, PRIMEDAuditResult
from primed.primed_anvil.tables import BooleanIconColumn

from ..models import dbGaPApplication

User = get_user_model()


@dataclass
class CollaboratorAuditResult(PRIMEDAuditResult):
    """Base class to hold results for auditing collaborators for a dbGaP application."""

    dbgap_application: dbGaPApplication
    collaborator: User
    member: Union[Account, ManagedGroup]
    note: str
    has_access: bool
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
            "collaborator": self.collaborator,
            "member": self.member,
            "has_access": self.has_access,
            "note": self.note,
            "action": self.action,
            "action_url": self.get_action_url(),
        }
        return row


@dataclass
class VerifiedAccess(CollaboratorAuditResult):
    """Audit results class for when access has been verified."""

    has_access: bool = True

    def __str__(self):
        return f"Verified access: {self.note}"


@dataclass
class VerifiedNoAccess(CollaboratorAuditResult):
    """Audit results class for when no access has been verified."""

    has_access: bool = False

    def __str__(self):
        return f"Verified no access: {self.note}"


@dataclass
class GrantAccess(CollaboratorAuditResult):
    """Audit results class for when access should be granted."""

    has_access: bool = False
    action: str = "Grant access"

    def __str__(self):
        return f"Grant access: {self.note}"


@dataclass
class RemoveAccess(CollaboratorAuditResult):
    """Audit results class for when access should be removed for a known reason."""

    has_access: bool = True
    action: str = "Remove access"

    def __str__(self):
        return f"Remove access: {self.note}"


@dataclass
class Error(CollaboratorAuditResult):
    """Audit results class for when an error has been detected (e.g., has access and never should have)."""

    pass


class dbGaPCollaboratorAuditTable(tables.Table):
    """A table to show results from a dbGaPCollaboratorAudit subclass."""

    application = tables.Column(linkify=True)
    collaborator = tables.Column(linkify=True)
    member = tables.Column(linkify=True)
    has_access = BooleanIconColumn(show_false_icon=True)
    note = tables.Column()
    action = tables.TemplateColumn(template_name="dbgap/snippets/dbgap_audit_action_button.html")

    class Meta:
        attrs = {"class": "table align-middle"}


class dbGaPCollaboratorAudit(PRIMEDAudit):
    """Audit collaborators for a dbGaP application."""

    # Access verified.
    PI_IN_ACCESS_GROUP = "PI is in the access group."
    COLLABORATOR_IN_ACCESS_GROUP = "Collaborator is in the access group."

    # Allowed reasons for no access.
    PI_NO_ACCOUNT = "PI has not linked an AnVIL account."
    COLLABORATOR_NO_ACCOUNT = "Collaborator has not linked an AnVIL account."

    # Allowed reasons to grant or remove access.
    PI_LINKED_ACCOUNT = "PI has a linked AnVIL account."
    COLLABORATOR_LINKED_ACCOUNT = "Collaborator has a linked AnVIL account."
    NOT_COLLABORATOR = "Not a collaborator."

    # # Unexpected.
    # ERROR_HAS_ACCESS = "Has access for an unknown reason."
    UNEXPECTED_GROUP_ACCESS = "Group has access for an unknown reason."

    results_table_class = dbGaPCollaboratorAuditTable

    def __init__(self, queryset=None):
        super().__init__()
        if queryset is None:
            queryset = dbGaPApplication.objects.all()
        if not (isinstance(queryset, QuerySet) and queryset.model is dbGaPApplication):
            raise ValueError("dbgap_application_queryset must be a queryset of dbGaPApplication objects.")
        self.queryset = queryset

    def _run_audit(self):
        for dbgap_application in self.queryset:
            self.audit_application(dbgap_application)

    def audit_application(self, dbgap_application):
        """Audit access for a specific dbGaP application."""
        # Get a list of every account in the access group.
        # accounts_with_access = list(GroupAccountMembership.objects.filter(group=dbgap_application.anvil_access_group))
        accounts_with_access = list(
            Account.objects.filter(groupaccountmembership__group=dbgap_application.anvil_access_group)
        )
        # Get a list of the PI and collaborators.
        users_to_audit = [dbgap_application.principal_investigator] + list(dbgap_application.collaborators.all())
        for user in users_to_audit:
            self._audit_application_and_user(dbgap_application, user)
            try:
                accounts_with_access.remove(user.account)
            except AttributeError:
                # The user is not in the access group - this is handled in the audit.
                pass
            except ValueError:
                # The user is not in the access group - this is handled in the audit.
                pass

        # If there are any accounts left, they should not have access.
        for account in accounts_with_access:
            self.needs_action.append(
                RemoveAccess(
                    dbgap_application=dbgap_application,
                    collaborator=account.user,
                    member=account,
                    note=self.NOT_COLLABORATOR,
                )
            )

        # Check group access. Most groups should not have access.
        group_memberships = GroupGroupMembership.objects.filter(
            parent_group=dbgap_application.anvil_access_group,
        ).exclude(
            # Ignore cc admins group - it is handled differently because it should have admin privileges.
            child_group__name="PRIMED_CC_ADMINS",
        )
        for group_membership in group_memberships:
            self.errors.append(
                RemoveAccess(
                    dbgap_application=dbgap_application,
                    collaborator=None,
                    member=group_membership.child_group,
                    note=self.UNEXPECTED_GROUP_ACCESS,
                )
            )

    def _audit_application_and_user(self, dbgap_application, user):
        """Audit access for a specific dbGaP application and a specific user."""
        is_pi = user == dbgap_application.principal_investigator
        is_collaborator = user in dbgap_application.collaborators.all()

        # Check if the user has a linked account.
        try:
            account = Account.objects.get(user=user)
        except Account.DoesNotExist:
            if is_pi:
                note = self.PI_NO_ACCOUNT
            elif is_collaborator:
                note = self.COLLABORATOR_NO_ACCOUNT
            else:
                note = self.NOT_COLLABORATOR
            self.verified.append(
                VerifiedNoAccess(
                    dbgap_application=dbgap_application,
                    collaborator=user,
                    member=None,
                    note=note,
                )
            )
            return

        # Check if the account is in the access group.
        is_in_access_group = GroupAccountMembership.objects.filter(
            account=user.account, group=dbgap_application.anvil_access_group
        ).exists()

        if is_in_access_group:
            if is_pi:
                self.verified.append(
                    VerifiedAccess(
                        dbgap_application=dbgap_application,
                        collaborator=user,
                        member=account,
                        note=self.PI_IN_ACCESS_GROUP,
                    )
                )
            elif is_collaborator:
                self.verified.append(
                    VerifiedAccess(
                        dbgap_application=dbgap_application,
                        collaborator=user,
                        member=account,
                        note=self.COLLABORATOR_IN_ACCESS_GROUP,
                    )
                )
            else:
                self.needs_action.append(
                    RemoveAccess(
                        dbgap_application=dbgap_application,
                        collaborator=user,
                        member=account,
                        note=self.NOT_COLLABORATOR,
                    )
                )
        else:
            if is_pi:
                self.needs_action.append(
                    GrantAccess(
                        dbgap_application=dbgap_application,
                        collaborator=user,
                        member=account,
                        note=self.PI_LINKED_ACCOUNT,
                    )
                )
            elif is_collaborator:
                self.needs_action.append(
                    GrantAccess(
                        dbgap_application=dbgap_application,
                        collaborator=user,
                        member=account,
                        note=self.COLLABORATOR_LINKED_ACCOUNT,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        dbgap_application=dbgap_application,
                        collaborator=user,
                        member=account,
                        note=self.NOT_COLLABORATOR,
                    )
                )
