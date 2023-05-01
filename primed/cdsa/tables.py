"""Tables for the `cdsa` app."""

import django_tables2 as tables

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

    class Meta:
        model = models.SignedAgreement
        fields = (
            "cc_id",
            "representative",
            "representative_role",
            "signing_institution",
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
    group = tables.Column(accessor="pk")

    class Meta:
        model = models.SignedAgreement
        fields = (
            "cc_id",
            "representative__name",
            "representative_role",
            "signing_institution",
            "group",
            "type",
            "is_primary",
        )

    def render_group(self, record):
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
