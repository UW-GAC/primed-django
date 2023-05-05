from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from . import models


@admin.register(models.AgreementVersion)
class AgreementVersion(SimpleHistoryAdmin):
    """Admin class for the `AgreementVersion` model."""

    list_display = (
        "full_version",
        "major_version",
        "minor_version",
        "date_approved",
    )
    list_filter = ("major_version",)
    sortable_by = (
        "major_version",
        "minor_version",
        "date_approved",
    )


@admin.register(models.SignedAgreement)
class SignedAgreement(SimpleHistoryAdmin):
    """Admin class for the `SignedAgreement` model."""

    list_display = (
        "cc_id",
        "representative",
        "type",
        "is_primary",
        "date_signed",
        "version",
    )
    list_filter = (
        "type",
        "is_primary",
        "version",
    )
    search_fields = (
        "representative",
        "full_name",
    )
    sortable_by = (
        "cc_id",
        "representative",
        "type",
        "version",
        "date_signed",
    )


@admin.register(models.MemberAgreement)
class MemberAgreementAdmin(SimpleHistoryAdmin):
    """Admin class for the `MemberAgreement` model."""

    list_display = (
        "signed_agreement",
        "study_site",
    )
    list_filter = (
        "study_site",
        "signed_agreement__is_primary",
    )


@admin.register(models.DataAffiliateAgreement)
class DataAffiliateAgreementAdmin(SimpleHistoryAdmin):
    """Admin class for the `DataAffiliateAgreement` model."""

    list_display = (
        "signed_agreement",
        "study",
    )
    list_filter = (
        "study",
        "signed_agreement__is_primary",
    )


@admin.register(models.NonDataAffiliateAgreement)
class NonDataAffiliateAgreementAdmin(SimpleHistoryAdmin):
    """Admin class for the `NonDataAffiliateAgreement` model."""

    list_display = (
        "signed_agreement",
        "affiliation",
    )
    list_filter = ("signed_agreement__is_primary",)


@admin.register(models.CDSAWorkspace)
class CDSAWorkspaceAdmin(SimpleHistoryAdmin):
    """Admin class for the `CDSAWorkspace` model."""

    list_displa = (
        "workspace",
        "available_data",
        "data_use_permission",
        "data_use_modifiers",
    )