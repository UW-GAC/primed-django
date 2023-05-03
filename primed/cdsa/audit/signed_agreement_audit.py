# from abc import ABC
from dataclasses import dataclass

# import django_tables2 as tables
from anvil_consortium_manager.models import GroupGroupMembership, ManagedGroup
from django.conf import settings
from django.urls import reverse

# from . import models
from .. import models

# from django.utils.safestring import mark_safe


# Dataclasses for storing audit results?
@dataclass
class AccessAuditResult:
    """Base class to hold results for auditing CDSA access for a specific SignedAgreement."""

    note: str
    signed_agreement: models.SignedAgreement

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

    # def get_table_dictionary(self):
    #     """Return a dictionary that can be used to populate an instance of `CDSAAccessSnapshotAuditTable`."""
    #     row = {
    #         "workspace": self.workspace,
    #         "signed_agreement": self.signed_agreement,
    #         "note": self.note,
    #         "action": self.get_action(),
    #         "action_url": self.get_action_url(),
    #     }
    #     return row


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
                self.anvil_cdsa_group,
                self.signed_agreement.anvil_access_group,
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
                self.anvil_cdsa_group,
                self.signed_agreement.anvil_access_group,
            ],
        )


@dataclass
class OtherError(AccessAuditResult):
    """Audit results class for when an error has been detected (e.g., has access and never should have)."""

    pass


# class CDSAAccessAuditTable(tables.Table):
#     """A table to show results from a CDSAAccessAudit subclass."""
#
#     workspace = tables.Column(linkify=True)
#     signed_agreement = tables.Column(linkify=True)
#     note = tables.Column()
#     action = tables.Column()
#
#     class Meta:
#         attrs = {"class": "table align-middle"}
#
#     def render_action(self, record, value):
#         return mark_safe(
#             """<a href="{}" class="btn btn-primary btn-sm">{}</a>""".format(
#                 record["action_url"], value
#             )
#         )
#
#


class SignedAgreementAccessAudit:
    """Audit for Signed Agreements."""

    # Access verified.
    VALID_CDSA = "Valid Signed Agreement."

    # Allowed reasons for no access.
    NO_PRIMARY_CDSA = "No primary CDSA for this group exists."

    # Other errors
    ERROR_OTHER_CASE = "Signed Agreement did not match any expected situations."

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

    # Audit a single signed agreement.
    def _audit_signed_agreement(self, signed_agreement):
        # Check if the access group is in the overall CDSA group.
        in_cdsa_group = GroupGroupMembership.objects.filter(
            parent_group=self.anvil_cdsa_group,
            child_group=signed_agreement.anvil_access_group,
        ).exists()
        # Primary agreements don't need to check components.
        if signed_agreement.is_primary and in_cdsa_group:
            self.verified.append(
                VerifiedAccess(
                    signed_agreement=signed_agreement,
                    note=self.VALID_CDSA,
                )
            )
            return
        elif signed_agreement.is_primary and not in_cdsa_group:
            self.needs_action.append(
                GrantAccess(
                    signed_agreement=signed_agreement,
                    note=self.VALID_CDSA,
                )
            )
            return
        elif not signed_agreement.is_primary:
            # component agreements need to check for a primary.
            if hasattr(signed_agreement, "memberagreement"):
                # Member
                primary_exists = models.MemberAgreement.objects.filter(
                    signed_agreement__is_primary=True,
                    study_site=signed_agreement.memberagreement.study_site,
                ).exists()
            elif hasattr(signed_agreement, "dataaffiliateagreement"):
                # Data affiliate
                primary_exists = models.DataAffiliateAgreement.objects.filter(
                    signed_agreement__is_primary=True,
                    study=signed_agreement.dataaffiliateagreement.study,
                ).exists()
            elif hasattr(signed_agreement, "nondataaffiliateagreement"):
                # Non-data affiliate should not have components so this is an error.
                raise RuntimeError(
                    "Non data affiliates should always be a primary CDSA."
                )
            else:
                # Some other case happened - log it as an error.
                self.errors.append(
                    OtherError(
                        signed_agreement=signed_agreement, note=self.ERROR_OTHER_CASE
                    )
                )
                return

            # Now check access for the component given the primary agreement.
            if primary_exists and in_cdsa_group:
                self.verified.append(
                    VerifiedAccess(
                        signed_agreement=signed_agreement,
                        note=self.VALID_CDSA,
                    )
                )
                return
            elif primary_exists and not in_cdsa_group:
                self.needs_action.append(
                    GrantAccess(
                        signed_agreement=signed_agreement,
                        note=self.VALID_CDSA,
                    )
                )
                return
            elif not primary_exists and not in_cdsa_group:
                self.verified.append(
                    VerifiedNoAccess(
                        signed_agreement=signed_agreement,
                        note=self.NO_PRIMARY_CDSA,
                    )
                )
                return
            elif not primary_exists and in_cdsa_group:
                self.errors.append(
                    RemoveAccess(
                        signed_agreement=signed_agreement,
                        note=self.NO_PRIMARY_CDSA,
                    )
                )
                return

        # If we made it this far in audit, some other case happened - log it as an error.
        self.errors.append(
            OtherError(signed_agreement=signed_agreement, note=self.ERROR_OTHER_CASE)
        )

    def run_audit(self):
        """Run an audit on all SignedAgreements."""
        for signed_agreement in models.SignedAgreement.objects.all():
            self._audit_signed_agreement(signed_agreement)
        self.completed = True


# class CDSAAccessAudit(ABC):
#
#     # Access verified.
#     VALID_CDSA = "Valid Signed Agreement."
#
#     # # Allowed reasons for no access.
#     NO_PRIMARY_CDSA = "No primary CDSA for this group exists."
#     # NO_SNAPSHOTS = "No snapshots for this application."
#     # NO_DAR = "No matching DAR."
#     # DAR_NOT_APPROVED = "DAR is not approved."
#     #
#     # # Allowed reasons to grant or remove access.
#     NEW_VALID_CDSA = "New valid Signed Agreement."
#     NEW_WORKSPACE = "New workspace."
#     # PREVIOUS_APPROVAL = "Previously approved."
#
#     # Unexpected.
#     ERROR_HAS_ACCESS = "Has access for an unknown reason."
#
#     # results_table_class = CDSAAccessAuditTable
#
#     def __init__(self):
#         self.completed = False
#         # Set up lists to hold audit results.
#         self.verified = None
#         self.needs_action = None
#         self.errors = None
#
#     def audit_agreement_and_workspace(self, signed_agreement, cdsa_workspace):
#         """Audit access for a specific SignedAgreement and a specific CDSA workspace."""
#         # First, check if the access group is in the auth domain for the workspace.
#         in_auth_domain = cdsa_workspace.workspace.is_in_authorization_domain(
#             signed_agreement.anvil_access_group
#         )
#
#     def get_verified_table(self):
#         """Return a table of verified results."""
#         return self.results_table_class(
#             [x.get_table_dictionary() for x in self.verified]
#         )
#
#     def get_needs_action_table(self):
#         """Return a table of results where action is needed."""
#         return self.results_table_class(
#             [x.get_table_dictionary() for x in self.needs_action]
#         )
#
#     def get_errors_table(self):
#         """Return a table of audit errors."""
#         return self.results_table_class([x.get_table_dictionary() for x in self.errors])
#

# class SignedAgreementAccessAudit(CDSAAccessAudit):
#     def __init__(self, signed_agreement):
#         super().__init__()
#         self.signed_agreement = signed_agreement
#
#     def run_audit(self):
#         """Audit all workspaces against access provided by this SignedAgreement."""
#         self.verified = []
#         self.needs_action = []
#         self.errors = []
#
#         # Get a list of all dbGaP workspaces.
#         dbgap_workspaces = CDSAWorkspace.objects.all()
#         # Loop through workspaces and verify access.
#         for dbgap_workspace in dbgap_workspaces:
#             self.audit_application_and_workspace(
#                 self.dbgap_application, dbgap_workspace
#             )
#         self.completed = True
#
#
# class CDSAWorkspaceAccessAudit(CDSAAccessAudit):
#     def __init__(self, dbgap_workspace):
#         super().__init__()
#         self.dbgap_workspace = dbgap_workspace
#
#     def run_audit(self):
#         """Audit this workspace against access provided by all dbGaPApplications."""
#         self.verified = []
#         self.needs_action = []
#         self.errors = []
#
#         # Get a list of all dbGaP applications.
#         dbgap_applications = dbGaPApplication.objects.all()
#         # Loop through workspaces and verify access.
#         for dbgap_application in dbgap_applications:
#             self.audit_application_and_workspace(
#                 dbgap_application, self.dbgap_workspace
#             )
#         self.completed = True
