from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from . import models


@admin.register(models.SignedAgreement)
class SignedAgreement(SimpleHistoryAdmin):
    """Admin class for the `SignedAgreement` model."""

    list_display = (
        "cc_id",
        "representative",
        "type",
        "date_last_signed",
    )
    list_filter = (
        "type",
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
        "date_last_signed",
    )
