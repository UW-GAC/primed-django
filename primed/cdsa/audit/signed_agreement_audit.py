# from abc import ABC
from dataclasses import dataclass

import django_tables2 as tables
from anvil_consortium_manager.models import ManagedGroup
from django.conf import settings
from django.db.models import QuerySet
from django.urls import reverse

from primed.primed_anvil.audit import PRIMEDAudit, PRIMEDAuditResult

from .. import models


# Dataclasses for storing audit results?
@dataclass
class AccessAuditResult(PRIMEDAuditResult):
    """Base class to hold results for auditing CDSA access for a specific SignedAgreement."""

    note: str
    signed_agreement: models.SignedAgreement
    action: str = None

    def __post_init__(self):
        self.anvil_cdsa_group = ManagedGroup.objects.get(name=settings.ANVIL_CDSA_GROUP_NAME)

    def get_action_url(self):
        """The URL that handles the action needed."""
        return reverse(
            "cdsa:audit:signed_agreements:sag:resolve",
            args=[
                self.signed_agreement,
            ],
        )

    def get_table_dictionary(self):
        """Return a dictionary that can be used to populate an instance of `SignedAgreementAccessAuditTable`."""
        row = {
            "signed_agreement": self.signed_agreement,
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


class SignedAgreementAccessAuditTable(tables.Table):
    """A table to show results from a SignedAgreementAccessAudit instance."""

    signed_agreement = tables.Column(linkify=True)
    agreement_group = tables.Column(accessor="signed_agreement__agreement_group")
    agreement_type = tables.Column(accessor="signed_agreement__combined_type")
    agreement_version = tables.Column(accessor="signed_agreement__version")
    note = tables.Column()
    action = tables.TemplateColumn(template_name="cdsa/snippets/signedagreement_audit_action_button.html")

    class Meta:
        attrs = {"class": "table align-middle"}


class SignedAgreementAccessAudit(PRIMEDAudit):
    """Audit for Signed Agreements."""

    # Access verified.
    ACTIVE_PRIMARY_AGREEMENT = "Active primary CDSA."
    ACTIVE_COMPONENT_AGREEMENT = "Active component CDSA with active primary."

    # Allowed reasons for no access.
    INACTIVE_AGREEMENT = "CDSA is inactive."
    # INVALID_AGREEMENT_VERSION = "CDSA version is not valid."
    NO_PRIMARY_AGREEMENT = "No primary CDSA for this group exists."
    PRIMARY_NOT_ACTIVE = "Primary agreement for this CDSA is not active."

    # Other errors
    ERROR_OTHER_CASE = "Signed Agreement did not match any expected situations."

    results_table_class = SignedAgreementAccessAuditTable

    def __init__(self, signed_agreement_queryset=None):
        super().__init__()
        # Store the queryset to run the audit on.
        if signed_agreement_queryset is None:
            signed_agreement_queryset = models.SignedAgreement.objects.all()
        if not (
            isinstance(signed_agreement_queryset, QuerySet)
            and signed_agreement_queryset.model is models.SignedAgreement
        ):
            raise ValueError("signed_agreement_queryset must be a queryset of SignedAgreement objects.")
        self.signed_agreement_queryset = signed_agreement_queryset

    def _audit_primary_agreement(self, signed_agreement):
        """Audit a single component signed agreement.

        The following items are checked:
        * if the primary agreement is active.
        * if the primary agreement is in the CDSA group.

        This audit does *not* check if the AgreementMajorVersion associated with the SignedAgreement is valid.
        """
        in_cdsa_group = signed_agreement.is_in_cdsa_group()
        is_active = signed_agreement.status == models.SignedAgreement.StatusChoices.ACTIVE

        if is_active:
            if in_cdsa_group:
                self.verified.append(
                    VerifiedAccess(
                        signed_agreement=signed_agreement,
                        note=self.ACTIVE_PRIMARY_AGREEMENT,
                    )
                )
                return
            else:
                self.needs_action.append(
                    GrantAccess(
                        signed_agreement=signed_agreement,
                        note=self.ACTIVE_PRIMARY_AGREEMENT,
                    )
                )
                return
        else:
            if in_cdsa_group:
                self.needs_action.append(
                    RemoveAccess(
                        signed_agreement=signed_agreement,
                        note=self.INACTIVE_AGREEMENT,
                    )
                )
                return
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        signed_agreement=signed_agreement,
                        note=self.INACTIVE_AGREEMENT,
                    )
                )
                return

        # If we made it this far in audit, some other case happened - log it as an error.
        # Haven't figured out a test for this because it is unexpected.
        self.errors.append(  # pragma: no cover
            OtherError(signed_agreement=signed_agreement, note=self.ERROR_OTHER_CASE)  # pragma: no cover
        )  # pragma: no cover

    def _audit_component_agreement(self, signed_agreement):
        """Audit a single component signed agreement.

        The following items are checked:
        * If a primary agreement exists
        # If the primary agreement is active
        * if the component agreement is active
        * if the component agreement is in the CDSA group

        This audit does *not* check if the AgreementMajorVersion associated with either the
        SignedAgreement or its component is valid.
        """
        in_cdsa_group = signed_agreement.is_in_cdsa_group()
        is_active = signed_agreement.status == models.SignedAgreement.StatusChoices.ACTIVE

        # Get the set of potential primary agreements for this component.
        if hasattr(signed_agreement, "memberagreement"):
            # Member
            primary_qs = models.SignedAgreement.objects.filter(
                memberagreement__is_primary=True,
                memberagreement__study_site=signed_agreement.memberagreement.study_site,
            )
        elif hasattr(signed_agreement, "dataaffiliateagreement"):
            # Data affiliate
            primary_qs = models.SignedAgreement.objects.filter(
                dataaffiliateagreement__is_primary=True,
                dataaffiliateagreement__study=signed_agreement.dataaffiliateagreement.study,
            )
        primary_exists = primary_qs.exists()
        primary_active = primary_qs.filter(
            status=models.SignedAgreement.StatusChoices.ACTIVE,
        ).exists()

        if primary_exists:
            if primary_active:
                if is_active:
                    if in_cdsa_group:
                        self.verified.append(
                            VerifiedAccess(
                                signed_agreement=signed_agreement,
                                note=self.ACTIVE_COMPONENT_AGREEMENT,
                            )
                        )
                        return
                    else:
                        self.needs_action.append(
                            GrantAccess(
                                signed_agreement=signed_agreement,
                                note=self.ACTIVE_COMPONENT_AGREEMENT,
                            )
                        )
                        return
                else:
                    if in_cdsa_group:
                        self.needs_action.append(
                            RemoveAccess(
                                signed_agreement=signed_agreement,
                                note=self.INACTIVE_AGREEMENT,
                            )
                        )
                        return
                    else:
                        self.verified.append(
                            VerifiedNoAccess(
                                signed_agreement=signed_agreement,
                                note=self.INACTIVE_AGREEMENT,
                            )
                        )
                        return
            else:
                if in_cdsa_group:
                    self.needs_action.append(
                        RemoveAccess(
                            signed_agreement=signed_agreement,
                            note=self.PRIMARY_NOT_ACTIVE,
                        )
                    )
                    return
                else:
                    self.verified.append(
                        VerifiedNoAccess(
                            signed_agreement=signed_agreement,
                            note=self.PRIMARY_NOT_ACTIVE,
                        )
                    )
                    return
        else:
            if in_cdsa_group:
                self.errors.append(
                    RemoveAccess(
                        signed_agreement=signed_agreement,
                        note=self.NO_PRIMARY_AGREEMENT,
                    )
                )
                return
            else:
                self.verified.append(
                    VerifiedNoAccess(
                        signed_agreement=signed_agreement,
                        note=self.NO_PRIMARY_AGREEMENT,
                    )
                )
                return

        # If we made it this far in audit, some other case happened - log it as an error.
        # Haven't figured out a test for this because it is unexpected.
        self.errors.append(  # pragma: no cover
            OtherError(signed_agreement=signed_agreement, note=self.ERROR_OTHER_CASE)  # pragma: no cover
        )  # pragma: no cover

    def _audit_signed_agreement(self, signed_agreement):
        agreement_type = signed_agreement.get_agreement_type()
        if not hasattr(agreement_type, "is_primary") or agreement_type.is_primary:
            self._audit_primary_agreement(signed_agreement)
        else:
            self._audit_component_agreement(signed_agreement)

    def _run_audit(self):
        """Run an audit on all SignedAgreements."""
        for signed_agreement in self.signed_agreement_queryset:
            self._audit_signed_agreement(signed_agreement)
