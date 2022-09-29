from django.contrib import admin

from . import models


@admin.register(models.dbGaPStudy)
class dbGaPStudyAdmin(admin.ModelAdmin):
    """Admin class for the `dbGaPStudy` model."""

    list_display = (
        "study",
        "phs",
    )
    search_fields = ("short_name",)
    sortable_by = (
        "short_name",
        "full_name",
    )


@admin.register(models.dbGaPWorkspace)
class dbGaPWorkspaceAdmin(admin.ModelAdmin):
    """Admin class for the `dbGaPWorkspace` model."""

    list_display = (
        "id",
        "workspace",
        "dbgap_study",
        "dbgap_version",
        "dbgap_participant_set",
        "full_consent_code",
    )
    list_filter = (
        "dbgap_study",
        "full_consent_code",
    )
    sortable_by = (
        "id",
        "workspace",
        "version",
    )
