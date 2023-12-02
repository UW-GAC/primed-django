"""Tables for the `cdsa` app."""

import django_tables2 as tables
from anvil_consortium_manager.models import (
    GroupAccountMembership,
    Workspace,
    WorkspaceGroupSharing,
)

from primed.primed_anvil.tables import (
    BooleanIconColumn,
    WorkspaceSharedWithConsortiumColumn,
)

from . import models


class AgreementVersionTable(tables.Table):

    major_version = tables.Column(linkify=True)
    full_version = tables.Column(
        linkify=True, order_by=("major_version", "minor_version")
    )
    major_version__is_valid = BooleanIconColumn(
        verbose_name="Valid?", show_false_icon=True
    )

    class Meta:
        model = models.AgreementVersion
        fields = (
            "major_version",
            "full_version",
            "major_version__is_valid",
            "date_approved",
        )


class SignedAgreementTable(tables.Table):

    cc_id = tables.Column(linkify=True)
    representative__name = tables.Column(
        linkify=lambda record: record.representative.get_absolute_url(),
        verbose_name="Representative",
    )
    representative_role = tables.Column(verbose_name="Role")
    agreement_type = tables.Column(
        accessor="combined_type", order_by=("type", "-is_primary")
    )
    number_accessors = tables.Column(
        verbose_name="Number of accessors",
        accessor="anvil_access_group__groupaccountmembership_set__count",
    )
    agreement_group = tables.Column(
        linkify=lambda record: record.agreement_group.get_absolute_url()
        if hasattr(record.agreement_group, "get_absolute_url")
        else None
    )
    version = tables.Column(linkify=True)

    class Meta:
        model = models.SignedAgreement
        fields = (
            "cc_id",
            "representative__name",
            "representative_role",
            "signing_institution",
            "agreement_group",
            "agreement_type",
            "version",
            "status",
            "date_signed",
            "number_accessors",
        )
        order_by = ("cc_id",)


class MemberAgreementTable(tables.Table):
    """Table to display `MemberAgreement` objects."""

    signed_agreement__cc_id = tables.Column(linkify=True)
    study_site = tables.Column(linkify=True)
    signed_agreement__is_primary = BooleanIconColumn(verbose_name="Primary?")
    signed_agreement__representative__name = tables.Column(
        linkify=lambda record: record.signed_agreement.representative.get_absolute_url(),
        verbose_name="Representative",
    )
    signed_agreement__representative_role = tables.Column(verbose_name="Role")
    number_accessors = tables.Column(
        verbose_name="Number of accessors",
        accessor="signed_agreement__anvil_access_group__groupaccountmembership_set__count",
    )
    signed_agreement__version = tables.Column(linkify=True)

    class Meta:
        model = models.MemberAgreement
        fields = (
            "signed_agreement__cc_id",
            "study_site",
            "signed_agreement__is_primary",
            "signed_agreement__representative__name",
            "signed_agreement__representative_role",
            "signed_agreement__signing_institution",
            "signed_agreement__version",
            "signed_agreement__status",
            "signed_agreement__date_signed",
            "number_accessors",
        )
        order_by = ("signed_agreement__cc_id",)


class DataAffiliateAgreementTable(tables.Table):
    """Table to display `DataAffiliateAgreement` objects."""

    signed_agreement__cc_id = tables.Column(linkify=True)
    study = tables.Column(linkify=True)
    signed_agreement__is_primary = BooleanIconColumn(verbose_name="Primary?")
    signed_agreement__representative__name = tables.Column(
        linkify=lambda record: record.signed_agreement.representative.get_absolute_url(),
        verbose_name="Representative",
    )
    signed_agreement__representative_role = tables.Column(verbose_name="Role")
    number_accessors = tables.Column(
        verbose_name="Number of accessors",
        accessor="signed_agreement__anvil_access_group__groupaccountmembership_set__count",
    )
    signed_agreement__version = tables.Column(linkify=True)

    class Meta:
        model = models.DataAffiliateAgreement
        fields = (
            "signed_agreement__cc_id",
            "study",
            "signed_agreement__is_primary",
            "signed_agreement__representative__name",
            "signed_agreement__representative_role",
            "signed_agreement__signing_institution",
            "signed_agreement__version",
            "signed_agreement__status",
            "signed_agreement__date_signed",
            "number_accessors",
        )
        order_by = ("signed_agreement__cc_id",)


class NonDataAffiliateAgreementTable(tables.Table):
    """Table to display `DataAffiliateAgreement` objects."""

    signed_agreement__cc_id = tables.Column(linkify=True)
    signed_agreement__representative__name = tables.Column(
        linkify=lambda record: record.signed_agreement.representative.get_absolute_url(),
        verbose_name="Representative",
    )
    signed_agreement__representative_role = tables.Column(verbose_name="Role")
    number_accessors = tables.Column(
        verbose_name="Number of accessors",
        accessor="signed_agreement__anvil_access_group__groupaccountmembership_set__count",
    )
    signed_agreement__version = tables.Column(linkify=True)

    class Meta:
        model = models.NonDataAffiliateAgreement
        fields = (
            "signed_agreement__cc_id",
            "affiliation",
            "signed_agreement__representative__name",
            "signed_agreement__representative_role",
            "signed_agreement__signing_institution",
            "signed_agreement__version",
            "signed_agreement__status",
            "signed_agreement__date_signed",
            "number_accessors",
        )
        order_by = ("signed_agreement__cc_id",)


class RepresentativeRecordsTable(tables.Table):
    """Table for a list of representatives that have signed the CDSA."""

    representative__name = tables.Column(verbose_name="Representative")
    signing_group = tables.Column(accessor="pk", orderable=False)
    agreement_type = tables.Column(
        accessor="combined_type", order_by=("type", "-is_primary")
    )

    class Meta:
        model = models.SignedAgreement
        fields = (
            "representative__name",
            "representative_role",
            "signing_institution",
            "signing_group",
            "agreement_type",
            "version",
        )
        order_by = ("representative__name",)

    def render_signing_group(self, record):
        if hasattr(record, "memberagreement"):
            value = record.memberagreement.study_site.short_name
        elif hasattr(record, "dataaffiliateagreement"):
            value = record.dataaffiliateagreement.study.short_name
        elif hasattr(record, "nondataaffiliateagreement"):
            value = record.nondataaffiliateagreement.affiliation
        else:
            value = None
        return value


class StudyRecordsTable(tables.Table):
    """Table for a list of studies that have signed the CDSA."""

    signed_agreement__representative__name = tables.Column(
        verbose_name="Representative"
    )
    # This will only order properly if the order_by value is a column in the table.
    study__short_name = tables.Column(verbose_name="Study")

    class Meta:
        model = models.DataAffiliateAgreement
        fields = (
            "study__short_name",
            "signed_agreement__representative__name",
        )
        order_by = ("study__short_name",)


class UserAccessRecordsTable(tables.Table):
    """Table tracking the users who have access to data via a CDSA."""

    group__signedagreement__signing_institution = tables.Column()
    group__signedagreement__representative__name = tables.Column(
        verbose_name="Signing representatitve",
    )
    signing_group = tables.Column(
        verbose_name="Signing group", accessor="group__signedagreement", orderable=False
    )

    class Meta:
        model = GroupAccountMembership
        fields = (
            "account__user__name",
            "signing_group",
            "group__signedagreement__signing_institution",
            "group__signedagreement__representative__name",
        )
        order_by = ("account__user__name",)

    def render_signing_group(self, record):
        if hasattr(record.group.signedagreement, "memberagreement"):
            value = record.group.signedagreement.memberagreement.study_site.short_name
        elif hasattr(record.group.signedagreement, "dataaffiliateagreement"):
            value = record.group.signedagreement.dataaffiliateagreement.study.short_name
        elif hasattr(record.group.signedagreement, "nondataaffiliateagreement"):
            value = record.group.signedagreement.nondataaffiliateagreement.affiliation
        else:
            return None
        return value


class CDSAWorkspaceRecordsTable(tables.Table):
    """CDSA workspace table for records reporting."""

    workspace__name = tables.Column()
    workspace__billing_project = tables.Column()
    study = tables.Column()
    data_use_permission__abbreviation = tables.Column(
        verbose_name="Data use permission"
    )
    data_use_modifiers = tables.ManyToManyColumn(
        transform=lambda x: x.abbreviation, verbose_name="Data use modifiers"
    )
    workspace__created = tables.columns.Column(verbose_name="Date created")
    date_shared = tables.columns.Column(accessor="pk", verbose_name="Date shared")

    class Meta:
        model = models.CDSAWorkspace
        fields = (
            "workspace__name",
            "workspace__billing_project",
            "study",
            "data_use_permission__abbreviation",
            "data_use_modifiers",
            "workspace__created",
            "date_shared",
        )
        order_by = ("workspace__name",)

    def render_date_shared(self, record):
        try:
            wgs = record.workspace.workspacegroupsharing_set.get(
                group__name="PRIMED_ALL"
            )
            return wgs.created
        except WorkspaceGroupSharing.DoesNotExist:
            return "—"


class CDSAWorkspaceStaffTable(tables.Table):
    """A table for the CDSAWorkspace model."""

    name = tables.Column(linkify=True)
    billing_project = tables.Column(linkify=True)
    cdsaworkspace__data_use_permission__abbreviation = tables.Column(
        verbose_name="DUO permission",
        linkify=lambda record: record.cdsaworkspace.data_use_permission.get_absolute_url(),
    )
    cdsaworkspace__study = tables.Column(linkify=True)
    cdsaworkspace__data_use_modifiers = tables.ManyToManyColumn(
        transform=lambda x: x.abbreviation,
        verbose_name="DUO modifiers",
        linkify_item=True,
    )
    is_shared = WorkspaceSharedWithConsortiumColumn()

    class Meta:
        model = Workspace
        fields = (
            "name",
            "billing_project",
            "cdsaworkspace__study",
            "cdsaworkspace__data_use_permission__abbreviation",
            "cdsaworkspace__data_use_modifiers",
        )
        order_by = ("name",)


class CDSAWorkspaceUserTable(tables.Table):
    """A table for the CDSAWorkspace model."""

    name = tables.Column()
    billing_project = tables.Column()
    cdsaworkspace__data_use_permission__abbreviation = tables.Column(
        verbose_name="DUO permission",
    )
    cdsaworkspace__study = tables.Column()
    cdsaworkspace__data_use_modifiers = tables.ManyToManyColumn(
        transform=lambda x: x.abbreviation,
        verbose_name="DUO modifiers",
    )
    is_shared = WorkspaceSharedWithConsortiumColumn()

    class Meta:
        model = Workspace
        fields = (
            "name",
            "billing_project",
            "cdsaworkspace__study",
            "cdsaworkspace__data_use_permission__abbreviation",
            "cdsaworkspace__data_use_modifiers",
        )
        order_by = ("name",)
