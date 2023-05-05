"""Tables for the `cdsa` app."""

import django_tables2 as tables
from anvil_consortium_manager.models import GroupAccountMembership
from django.utils.html import format_html

from primed.primed_anvil.tables import BooleanCheckColumn

from . import models


class SignedAgreementTable(tables.Table):

    cc_id = tables.Column(linkify=True)
    representative = tables.Column(linkify=True)
    representative_role = tables.Column(verbose_name="Role")
    combined_type = tables.Column(order_by=("type", "-is_primary"))
    number_accessors = tables.Column(
        verbose_name="Number of accessors",
        accessor="anvil_access_group__groupaccountmembership_set__count",
    )
    agreement_group = tables.Column(
        linkify=lambda record: record.agreement_group.get_absolute_url()
        if hasattr(record.agreement_group, "get_absolute_url")
        else None
    )

    class Meta:
        model = models.SignedAgreement
        fields = (
            "cc_id",
            "representative",
            "representative_role",
            "signing_institution",
            "agreement_group",
            "combined_type",
            "version",
            "date_signed",
            "number_accessors",
        )


class MemberAgreementTable(tables.Table):
    """Table to display `MemberAgreement` objects."""

    signed_agreement__cc_id = tables.Column(linkify=True)
    study_site = tables.Column(linkify=True)
    signed_agreement__is_primary = BooleanCheckColumn()
    signed_agreement__representative = tables.Column(linkify=True)
    signed_agreement__representative_role = tables.Column(verbose_name="Role")
    number_accessors = tables.Column(
        verbose_name="Number of accessors",
        accessor="signed_agreement__anvil_access_group__groupaccountmembership_set__count",
    )

    class Meta:
        model = models.MemberAgreement
        fields = (
            "signed_agreement__cc_id",
            "study_site",
            "signed_agreement__is_primary",
            "signed_agreement__representative",
            "signed_agreement__representative_role",
            "signed_agreement__signing_institution",
            "signed_agreement__version",
            "signed_agreement__date_signed",
            "number_accessors",
        )


class DataAffiliateAgreementTable(tables.Table):
    """Table to display `DataAffiliateAgreement` objects."""

    signed_agreement__cc_id = tables.Column(linkify=True)
    study = tables.Column(linkify=True)
    signed_agreement__is_primary = BooleanCheckColumn()
    signed_agreement__representative = tables.Column(linkify=True)
    signed_agreement__representative_role = tables.Column(verbose_name="Role")
    number_accessors = tables.Column(
        verbose_name="Number of accessors",
        accessor="signed_agreement__anvil_access_group__groupaccountmembership_set__count",
    )

    class Meta:
        model = models.DataAffiliateAgreement
        fields = (
            "signed_agreement__cc_id",
            "study",
            "signed_agreement__is_primary",
            "signed_agreement__representative",
            "signed_agreement__representative_role",
            "signed_agreement__signing_institution",
            "signed_agreement__version",
            "signed_agreement__date_signed",
            "number_accessors",
        )


class NonDataAffiliateAgreementTable(tables.Table):
    """Table to display `DataAffiliateAgreement` objects."""

    signed_agreement__cc_id = tables.Column(linkify=True)
    signed_agreement__is_primary = BooleanCheckColumn()
    signed_agreement__representative = tables.Column(linkify=True)
    signed_agreement__representative_role = tables.Column(verbose_name="Role")
    number_accessors = tables.Column(
        verbose_name="Number of accessors",
        accessor="signed_agreement__anvil_access_group__groupaccountmembership_set__count",
    )

    class Meta:
        model = models.NonDataAffiliateAgreement
        fields = (
            "signed_agreement__cc_id",
            "affiliation",
            "signed_agreement__is_primary",
            "signed_agreement__representative",
            "signed_agreement__representative_role",
            "signed_agreement__signing_institution",
            "signed_agreement__version",
            "signed_agreement__date_signed",
            "number_accessors",
        )


class RepresentativeRecordsTable(tables.Table):
    """Table for a list of representatives that have signed the CDSA."""

    representative__name = tables.Column(verbose_name="Representative")
    is_primary = BooleanCheckColumn()
    signing_group = tables.Column(accessor="pk", orderable=False)

    class Meta:
        model = models.SignedAgreement
        fields = (
            "cc_id",
            "representative__name",
            "representative_role",
            "signing_institution",
            "signing_group",
            "type",
            "is_primary",
        )

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

    class Meta:
        model = models.DataAffiliateAgreement
        fields = (
            "study",
            "signed_agreement__representative__name",
        )


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


class CDSAWorkspaceTable(tables.Table):
    """A table for the CDSAWorkspace model."""

    name = tables.Column(linkify=True)
    billing_project = tables.Column(linkify=True)
    cdsaworkspace__study = tables.Column(linkify=True)
    cdsaworkspace__data_use_modifiers = tables.ManyToManyColumn(
        transform=lambda x: x.abbreviation
    )
    is_shared = tables.columns.Column(
        accessor="pk",
        verbose_name="Shared with PRIMED?",
        orderable=False,
    )

    class Meta:
        model = models.CDSAWorkspace
        fields = (
            "name",
            "billing_project",
            "cdsaworkspace__study",
            "cdsaworkspace__data_use_permission__abbreviation",
            "cdsaworkspace__data_use_modifiers",
        )

    def render_is_shared(self, record):
        is_shared = record.workspacegroupsharing_set.filter(
            group__name="PRIMED_ALL"
        ).exists()
        if is_shared:
            icon = "check-circle-fill"
            color = "green"
            value = format_html(
                """<i class="bi bi-{}" style="color: {};"></i>""".format(icon, color)
            )
        else:
            value = ""
        return value
