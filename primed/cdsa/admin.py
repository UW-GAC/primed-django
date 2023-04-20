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
    list_filter = (
        "major_version",
    )
    sortable_by = (
        "major_version",
        "minor_version",
        "date_approved",
    )

# @admin.register(models.SignedAgreement)
# class SignedAgreement(SimpleHistoryAdmin):
#     """Admin class for the `SignedAgreement` model."""
#
#     list_display = (
#         "cc_id",
#         "representative",
#         "type",
#         "date_last_signed",
#     )
#     list_filter = (
#         "type",
#         "version",
#     )
#     search_fields = (
#         "representative",
#         "full_name",
#     )
#     sortable_by = (
#         "cc_id",
#         "representative",
#         "type",
#         "version",
#         "date_last_signed",
#     )
