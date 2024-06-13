from dataclasses import dataclass
from typing import Union

import django_tables2 as tables
from anvil_consortium_manager.models import Account, GroupAccountMembership, GroupGroupMembership, ManagedGroup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet

from primed.primed_anvil.audit import PRIMEDAudit, PRIMEDAuditResult
from primed.primed_anvil.tables import BooleanIconColumn

from ..models import dbGaPApplication

User = get_user_model()


@dataclass
class CollaboratorAuditResult(PRIMEDAuditResult):
    """Base class to hold results for auditing collaborators for a dbGaP application."""

    dbgap_application: dbGaPApplication
    user: User
    member: Union[Account, ManagedGroup]
    note: str
    has_access: bool
    action: str = None

    def __post_init__(self):
        if isinstance(self.member, Account) and hasattr(self.member, "user") and self.member.user != self.user:
            raise ValueError("Account and user do not match.")
        elif isinstance(self.member, ManagedGroup) and self.user:
            raise ValueError("Cannot specify both a ManagedGroup member and a User.")

    def get_action_url(self):
        """The URL that handles the action needed."""
        # This is handled in the template with htmx, so None is fine.
        return None

    def get_table_dictionary(self):
        """Return a dictionary that can be used to populate an instance of `dbGaPDataAccessSnapshotAuditTable`."""
        row = {
            "application": self.dbgap_application,
            "user": self.user,
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
    user = tables.Column(linkify=True)
    member = tables.Column(linkify=True)
    has_access = BooleanIconColumn(show_false_icon=True)
    note = tables.Column()
    action = tables.TemplateColumn(template_name="dbgap/snippets/dbgap_collaborator_audit_action_button.html")

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
    GROUP_WITHOUT_ACCESS = "Groups do not have access."

    # # Unexpected.
    # ERROR_HAS_ACCESS = "Has access for an unknown reason."
    UNEXPECTED_GROUP_ACCESS = "Group should not have access."
    ACCOUNT_NOT_LINKED_TO_USER = "Account is not linked to a user."

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
        # Get a list of everything to audit.
        pi = dbgap_application.principal_investigator
        collaborators = list(dbgap_application.collaborators.all())
        accounts_with_access = list(
            Account.objects.filter(
                # They are members of this group.
                groupaccountmembership__group=dbgap_application.anvil_access_group
            )
            .exclude(
                # Not collaborators.
                user__in=collaborators
            )
            .exclude(
                # Not the PI.
                user=pi
            )
        )
        groups_with_access = list(
            ManagedGroup.objects.filter(parent_memberships__parent_group=dbgap_application.anvil_access_group)
        )

        objs_to_audit = [pi] + collaborators + accounts_with_access + groups_with_access

        for obj in objs_to_audit:
            self.audit_application_and_object(dbgap_application, obj)

    def audit_application_and_object(self, dbgap_application, obj):
        """Audit access for a specific dbGaP application and generic object instance.

        obj can be a User, Account, ManagedGroup, or email string."""

        if isinstance(obj, str):
            try:
                instance = User.objects.get(username__iexact=obj)
            except User.DoesNotExist:
                # Next we'll check the account.
                try:
                    instance = Account.objects.get(email__iexact=obj)
                except Account.DoesNotExist:
                    try:
                        instance = ManagedGroup.objects.get(email__iexact=obj)
                    except ManagedGroup.DoesNotExist:
                        raise ValueError(f"Could not find a User, Account, or ManagedGroup with the email {obj}.")
        else:
            instance = obj

        # Now decide which sub-method to call.
        if isinstance(instance, User):
            self._audit_application_and_user(dbgap_application, instance)
        elif isinstance(instance, Account):
            self._audit_application_and_account(dbgap_application, instance)
        elif isinstance(instance, ManagedGroup):
            self._audit_application_and_group(dbgap_application, instance)
        else:
            raise ValueError("object must be a User, Account, ManagedGroup, or string.")

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
                    user=user,
                    member=None,
                    note=note,
                )
            )
            return

        self._audit_application_and_account(dbgap_application, account)

    def _audit_application_and_account(self, dbgap_application, account):
        # Check if the account is in the access group.
        is_in_access_group = GroupAccountMembership.objects.filter(
            account=account, group=dbgap_application.anvil_access_group
        ).exists()

        # Get the user.
        if hasattr(account, "user") and account.user:
            user = account.user
        else:
            if is_in_access_group:
                self.needs_action.append(
                    RemoveAccess(
                        dbgap_application=dbgap_application,
                        user=None,
                        member=account,
                        note=self.ACCOUNT_NOT_LINKED_TO_USER,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        dbgap_application=dbgap_application,
                        user=None,
                        member=account,
                        note=self.ACCOUNT_NOT_LINKED_TO_USER,
                    )
                )
            return

        is_pi = user == dbgap_application.principal_investigator
        is_collaborator = user in dbgap_application.collaborators.all()

        if is_in_access_group:
            if is_pi:
                self.verified.append(
                    VerifiedAccess(
                        dbgap_application=dbgap_application,
                        user=user,
                        member=account,
                        note=self.PI_IN_ACCESS_GROUP,
                    )
                )
            elif is_collaborator:
                self.verified.append(
                    VerifiedAccess(
                        dbgap_application=dbgap_application,
                        user=user,
                        member=account,
                        note=self.COLLABORATOR_IN_ACCESS_GROUP,
                    )
                )
            else:
                self.needs_action.append(
                    RemoveAccess(
                        dbgap_application=dbgap_application,
                        user=user,
                        member=account,
                        note=self.NOT_COLLABORATOR,
                    )
                )
        else:
            if is_pi:
                self.needs_action.append(
                    GrantAccess(
                        dbgap_application=dbgap_application,
                        user=user,
                        member=account,
                        note=self.PI_LINKED_ACCOUNT,
                    )
                )
            elif is_collaborator:
                self.needs_action.append(
                    GrantAccess(
                        dbgap_application=dbgap_application,
                        user=user,
                        member=account,
                        note=self.COLLABORATOR_LINKED_ACCOUNT,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        dbgap_application=dbgap_application,
                        user=user,
                        member=account,
                        note=self.NOT_COLLABORATOR,
                    )
                )

    def _audit_application_and_group(self, dbgap_application, group):
        """Audit access for a specific dbGaP application and a specific group."""
        in_access_group = GroupGroupMembership.objects.filter(
            child_group=group, parent_group=dbgap_application.anvil_access_group
        ).exists()
        if group.name == settings.ANVIL_CC_ADMINS_GROUP_NAME:
            pass
        else:
            if in_access_group:
                self.errors.append(
                    RemoveAccess(
                        dbgap_application=dbgap_application,
                        user=None,
                        member=group,
                        note=self.UNEXPECTED_GROUP_ACCESS,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        dbgap_application=dbgap_application,
                        user=None,
                        member=group,
                        note=self.GROUP_WITHOUT_ACCESS,
                    )
                )
