from dataclasses import dataclass
from typing import Union

import django_tables2 as tables
from anvil_consortium_manager.models import Account, GroupAccountMembership, GroupGroupMembership, ManagedGroup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet

from primed.primed_anvil.audit import PRIMEDAudit, PRIMEDAuditResult
from primed.primed_anvil.tables import BooleanIconColumn

from ..models import DataAffiliateAgreement

User = get_user_model()


@dataclass
class UploaderAuditResult(PRIMEDAuditResult):
    """Base class to hold results for auditing uploaders for a DataAffiliateAgreement."""

    data_affiliate_agreement: DataAffiliateAgreement
    note: str
    has_access: bool
    action: str = None
    user: User = None
    member: Union[Account, ManagedGroup] = None

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
            "data_affiliate_agreement": self.data_affiliate_agreement,
            "user": self.user,
            "member": self.member,
            "has_access": self.has_access,
            "note": self.note,
            "action": self.action,
            "action_url": self.get_action_url(),
        }
        return row


@dataclass
class VerifiedAccess(UploaderAuditResult):
    """Audit results class for when access has been verified."""

    has_access: bool = True

    def __str__(self):
        return f"Verified access: {self.note}"


@dataclass
class VerifiedNoAccess(UploaderAuditResult):
    """Audit results class for when no access has been verified."""

    has_access: bool = False

    def __str__(self):
        return f"Verified no access: {self.note}"


@dataclass
class GrantAccess(UploaderAuditResult):
    """Audit results class for when access should be granted."""

    has_access: bool = False
    action: str = "Grant access"

    def __str__(self):
        return f"Grant access: {self.note}"


@dataclass
class RemoveAccess(UploaderAuditResult):
    """Audit results class for when access should be removed for a known reason."""

    has_access: bool = True
    action: str = "Remove access"

    def __str__(self):
        return f"Remove access: {self.note}"


@dataclass
class Error(UploaderAuditResult):
    """Audit results class for when an error has been detected (e.g., has access and never should have)."""

    pass


class DataAffiliateUploaderAuditTable(tables.Table):
    """A table to show results from a DataAffiliateAgreementUploaderAudit subclass."""

    data_affiliate_agreement = tables.Column(linkify=True)
    user = tables.Column(linkify=True)
    member = tables.Column(linkify=True)
    has_access = BooleanIconColumn(show_false_icon=True)
    note = tables.Column()
    action = tables.TemplateColumn(template_name="cdsa/snippets/uploader_audit_action_button.html")

    class Meta:
        attrs = {"class": "table align-middle"}


class DataAffiliateUploaderAudit(PRIMEDAudit):
    """Audit collaborators for a DataAffiliateAgreement."""

    # Access verified.
    UPLOADER_IN_ACCESS_GROUP = "Uploader is in the access group."

    # Allowed reasons for no access.
    UPLOADER_NO_ACCOUNT = "Uploader has not linked an AnVIL account."

    # Allowed reasons to grant or remove access.
    UPLOADER_LINKED_ACCOUNT = "Uploader has a linked AnVIL account."
    NOT_UPLOADER = "Not an uploader."
    GROUP_WITHOUT_ACCESS = "Groups do not have access."

    # # Unexpected.
    # ERROR_HAS_ACCESS = "Has access for an unknown reason."
    UNEXPECTED_GROUP_ACCESS = "Group should not have access."
    ACCOUNT_NOT_LINKED_TO_USER = "Account is not linked to a user."

    results_table_class = DataAffiliateUploaderAuditTable

    def __init__(self, queryset=None):
        super().__init__()
        if queryset is None:
            queryset = DataAffiliateAgreement.objects.all()
        if not (isinstance(queryset, QuerySet) and queryset.model is DataAffiliateAgreement):
            raise ValueError("queryset must be a queryset of DataAffiliateAgreement objects.")
        self.queryset = queryset

    def _run_audit(self):
        for agreement in self.queryset:
            self.audit_agreement(agreement)

    def audit_agreement(self, data_affiliate_agreement):
        """Audit access for a specific DataAffiliateAgreement."""
        # Get a list of everything to audit.
        uploaders = list(data_affiliate_agreement.uploaders.all())
        accounts_with_access = list(
            Account.objects.filter(
                # They are members of this group.
                groupaccountmembership__group=data_affiliate_agreement.anvil_upload_group
            ).exclude(
                # Not uploaders; they are handled differently.
                user__in=uploaders
            )
        )
        groups_with_access = list(
            ManagedGroup.objects.filter(parent_memberships__parent_group=data_affiliate_agreement.anvil_upload_group)
        )

        objs_to_audit = uploaders + accounts_with_access + groups_with_access

        for obj in objs_to_audit:
            self.audit_agreement_and_object(data_affiliate_agreement, obj)

    def audit_agreement_and_object(self, data_affiliate_agreement, obj):
        """Audit access for a specific DataAffiliateAgreement and generic object instance.

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
            self._audit_agreement_and_user(data_affiliate_agreement, instance)
        elif isinstance(instance, Account):
            self._audit_agreement_and_account(data_affiliate_agreement, instance)
        elif isinstance(instance, ManagedGroup):
            self._audit_agreement_and_group(data_affiliate_agreement, instance)
        else:
            raise ValueError("object must be a User, Account, ManagedGroup, or string.")

    def _audit_agreement_and_user(self, data_affiliate_agreement, user):
        """Audit access for a specific DataAffiliateAgreement and a specific user."""
        is_uploader = user in data_affiliate_agreement.uploaders.all()

        # Check if the user has a linked account.
        try:
            account = Account.objects.get(user=user)
        except Account.DoesNotExist:
            if is_uploader:
                note = self.UPLOADER_NO_ACCOUNT
            else:
                note = self.NOT_UPLOADER
            self.verified.append(
                VerifiedNoAccess(
                    data_affiliate_agreement=data_affiliate_agreement,
                    user=user,
                    member=None,
                    note=note,
                )
            )
            return

        self._audit_agreement_and_account(data_affiliate_agreement, account)

    def _audit_agreement_and_account(self, data_affiliate_agreement, account):
        # Check if the account is in the access group.
        is_in_access_group = GroupAccountMembership.objects.filter(
            account=account, group=data_affiliate_agreement.anvil_upload_group
        ).exists()

        # Get the user.
        if hasattr(account, "user") and account.user:
            user = account.user
        else:
            if is_in_access_group:
                self.needs_action.append(
                    RemoveAccess(
                        data_affiliate_agreement=data_affiliate_agreement,
                        user=None,
                        member=account,
                        note=self.ACCOUNT_NOT_LINKED_TO_USER,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        data_affiliate_agreement=data_affiliate_agreement,
                        user=None,
                        member=account,
                        note=self.ACCOUNT_NOT_LINKED_TO_USER,
                    )
                )
            return

        is_uploader = user in data_affiliate_agreement.uploaders.all()

        if is_in_access_group:
            if is_uploader:
                self.verified.append(
                    VerifiedAccess(
                        data_affiliate_agreement=data_affiliate_agreement,
                        user=user,
                        member=account,
                        note=self.UPLOADER_IN_ACCESS_GROUP,
                    )
                )
            else:
                self.needs_action.append(
                    RemoveAccess(
                        data_affiliate_agreement=data_affiliate_agreement,
                        user=user,
                        member=account,
                        note=self.NOT_UPLOADER,
                    )
                )
        else:
            if is_uploader:
                self.needs_action.append(
                    GrantAccess(
                        data_affiliate_agreement=data_affiliate_agreement,
                        user=user,
                        member=account,
                        note=self.UPLOADER_LINKED_ACCOUNT,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        data_affiliate_agreement=data_affiliate_agreement,
                        user=user,
                        member=account,
                        note=self.NOT_UPLOADER,
                    )
                )

    def _audit_agreement_and_group(self, data_affiliate_agreement, group):
        """Audit access for a specific DataAffiliateAgreement and a specific group."""
        in_access_group = GroupGroupMembership.objects.filter(
            child_group=group, parent_group=data_affiliate_agreement.anvil_upload_group
        ).exists()
        if group.name == settings.ANVIL_CC_ADMINS_GROUP_NAME:
            pass
        else:
            if in_access_group:
                self.errors.append(
                    RemoveAccess(
                        data_affiliate_agreement=data_affiliate_agreement,
                        user=None,
                        member=group,
                        note=self.UNEXPECTED_GROUP_ACCESS,
                    )
                )
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        data_affiliate_agreement=data_affiliate_agreement,
                        user=None,
                        member=group,
                        note=self.GROUP_WITHOUT_ACCESS,
                    )
                )
