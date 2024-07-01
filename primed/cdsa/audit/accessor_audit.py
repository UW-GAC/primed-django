from dataclasses import dataclass
from typing import Union

import django_tables2 as tables
from anvil_consortium_manager.models import Account, GroupAccountMembership, GroupGroupMembership, ManagedGroup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet

from primed.primed_anvil.audit import PRIMEDAudit, PRIMEDAuditResult
from primed.primed_anvil.tables import BooleanIconColumn

from ..models import SignedAgreement

User = get_user_model()


@dataclass
class AccessorAuditResult(PRIMEDAuditResult):
    """Base class to hold results for auditing accessors for a SignedAgreement."""

    signed_agreement: SignedAgreement
    note: str
    has_access: bool
    user: User = None
    member: Union[Account, ManagedGroup] = None
    action: str = None

    def __post_init__(self):
        if isinstance(self.member, Account) and hasattr(self.member, "user") and self.member.user != self.user:
            raise ValueError("Account and user do not match.")
        elif isinstance(self.member, ManagedGroup) and self.user:
            raise ValueError("Cannot specify both a ManagedGroup member and a User.")

    def get_table_dictionary(self):
        """Return a dictionary that can be used to populate an instance of `dbGaPDataAccessSnapshotAuditTable`."""
        row = {
            "signed_agreement": self.signed_agreement,
            "user": self.user,
            "member": self.member,
            "has_access": self.has_access,
            "note": self.note,
            "action": self.action,
        }
        return row


@dataclass
class VerifiedAccess(AccessorAuditResult):
    """Audit results class for when access has been verified."""

    has_access: bool = True

    def __str__(self):
        return f"Verified access: {self.note}"


@dataclass
class VerifiedNoAccess(AccessorAuditResult):
    """Audit results class for when no access has been verified."""

    has_access: bool = False

    def __str__(self):
        return f"Verified no access: {self.note}"


@dataclass
class GrantAccess(AccessorAuditResult):
    """Audit results class for when access should be granted."""

    has_access: bool = False
    action: str = "Grant access"

    def __str__(self):
        return f"Grant access: {self.note}"


@dataclass
class RemoveAccess(AccessorAuditResult):
    """Audit results class for when access should be removed for a known reason."""

    has_access: bool = True
    action: str = "Remove access"

    def __str__(self):
        return f"Remove access: {self.note}"


@dataclass
class Error(AccessorAuditResult):
    """Audit results class for when an error has been detected (e.g., has access and never should have)."""

    pass


class AccessorAuditTable(tables.Table):
    """A table to show results from a AccessorAudit subclass."""

    signed_agreement = tables.Column(linkify=True)
    user = tables.Column(linkify=True)
    member = tables.Column(linkify=True)
    has_access = BooleanIconColumn(show_false_icon=True)
    note = tables.Column()
    action = tables.TemplateColumn(template_name="cdsa/snippets/accessor_audit_action_button.html")

    class Meta:
        attrs = {"class": "table align-middle"}


class AccessorAudit(PRIMEDAudit):
    """Audit collaborators for a SignedAgreement."""

    # Access verified.
    ACCESSOR_IN_ACCESS_GROUP = "Accessor is in the access group."

    # Allowed reasons for no access.
    ACCESSOR_NO_ACCOUNT = "Accessor has not linked an AnVIL account."

    # Allowed reasons to grant or remove access.
    ACCESSOR_LINKED_ACCOUNT = "Accessor has a linked AnVIL account."
    NOT_ACCESSOR = "Not an accessor."
    GROUP_WITHOUT_ACCESS = "Groups do not have access."

    # # Unexpected.
    # ERROR_HAS_ACCESS = "Has access for an unknown reason."
    UNEXPECTED_GROUP_ACCESS = "Group should not have access."
    ACCOUNT_NOT_LINKED_TO_USER = "Account is not linked to a user."

    results_table_class = AccessorAuditTable

    def __init__(self, queryset=None):
        super().__init__()
        if queryset is None:
            queryset = SignedAgreement.objects.all()
        if not (isinstance(queryset, QuerySet) and queryset.model is SignedAgreement):
            raise ValueError("signed_agreement_queryset must be a queryset of SignedAgreement objects.")
        self.queryset = queryset

    def _run_audit(self):
        for signed_agreement in self.queryset:
            self.audit_agreement(signed_agreement)

    def audit_agreement(self, signed_agreement):
        """Audit access for a specific SignedAgreement."""
        # Get a list of everything to audit.
        accessors = list(signed_agreement.accessors.all())
        accounts_with_access = list(
            Account.objects.filter(
                # They are members of this group.
                groupaccountmembership__group=signed_agreement.anvil_access_group
            ).exclude(
                # Not accessors; they are handled differently.
                user__in=accessors
            )
        )
        groups_with_access = list(
            ManagedGroup.objects.filter(parent_memberships__parent_group=signed_agreement.anvil_access_group)
        )

        objs_to_audit = accessors + accounts_with_access + groups_with_access

        for obj in objs_to_audit:
            self.audit_agreement_and_object(signed_agreement, obj)

    def audit_agreement_and_object(self, signed_agreement, obj):
        """Audit access for a specific SignedAgreement and generic object instance.

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
            self._audit_agreement_and_user(signed_agreement, instance)
        elif isinstance(instance, Account):
            self._audit_agreement_and_account(signed_agreement, instance)
        elif isinstance(instance, ManagedGroup):
            self._audit_agreement_and_group(signed_agreement, instance)
        else:
            raise ValueError("object must be a User, Account, ManagedGroup, or string.")

    def _audit_agreement_and_user(self, signed_agreement, user):
        """Audit access for a specific SignedAgreement and a specific user."""
        is_accessor = user in signed_agreement.accessors.all()

        # Check if the user has a linked account.
        try:
            account = Account.objects.get(user=user)
        except Account.DoesNotExist:
            if is_accessor:
                note = self.ACCESSOR_NO_ACCOUNT
            else:
                note = self.NOT_ACCESSOR
            self.verified.append(
                VerifiedNoAccess(
                    signed_agreement=signed_agreement,
                    user=user,
                    member=None,
                    note=note,
                )
            )
            return

        self._audit_agreement_and_account(signed_agreement, account)

    def _audit_agreement_and_account(self, signed_agreement, account):
        # Check if the account is in the access group.
        is_in_access_group = GroupAccountMembership.objects.filter(
            account=account, group=signed_agreement.anvil_access_group
        ).exists()

        # Get the user.
        if hasattr(account, "user") and account.user:
            user = account.user
        else:
            if is_in_access_group:
                self.needs_action.append(
                    RemoveAccess(
                        signed_agreement=signed_agreement,
                        user=None,
                        member=account,
                        note=self.ACCOUNT_NOT_LINKED_TO_USER,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        signed_agreement=signed_agreement,
                        user=None,
                        member=account,
                        note=self.ACCOUNT_NOT_LINKED_TO_USER,
                    )
                )
            return

        is_accessor = user in signed_agreement.accessors.all()

        if is_in_access_group:
            if is_accessor:
                self.verified.append(
                    VerifiedAccess(
                        signed_agreement=signed_agreement,
                        user=user,
                        member=account,
                        note=self.ACCESSOR_IN_ACCESS_GROUP,
                    )
                )
            else:
                self.needs_action.append(
                    RemoveAccess(
                        signed_agreement=signed_agreement,
                        user=user,
                        member=account,
                        note=self.NOT_ACCESSOR,
                    )
                )
        else:
            if is_accessor:
                self.needs_action.append(
                    GrantAccess(
                        signed_agreement=signed_agreement,
                        user=user,
                        member=account,
                        note=self.ACCESSOR_LINKED_ACCOUNT,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        signed_agreement=signed_agreement,
                        user=user,
                        member=account,
                        note=self.NOT_ACCESSOR,
                    )
                )

    def _audit_agreement_and_group(self, signed_agreement, group):
        """Audit access for a specific SignedAgreement and a specific group."""
        in_access_group = GroupGroupMembership.objects.filter(
            child_group=group, parent_group=signed_agreement.anvil_access_group
        ).exists()
        if group.name == settings.ANVIL_CC_ADMINS_GROUP_NAME:
            pass
        else:
            if in_access_group:
                self.errors.append(
                    RemoveAccess(
                        signed_agreement=signed_agreement,
                        user=None,
                        member=group,
                        note=self.UNEXPECTED_GROUP_ACCESS,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        signed_agreement=signed_agreement,
                        user=None,
                        member=group,
                        note=self.GROUP_WITHOUT_ACCESS,
                    )
                )
