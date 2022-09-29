from django.contrib import admin

from . import models


@admin.register(models.dbGaPWorkspace)
class dbGaPWorkspaceAdmin(admin.ModelAdmin):
    """Admin class for the `dbGaPWorkspace` model."""

    list_display = (
        "id",
        "workspace",
        "study",
        "phs",
        "version",
        "participant_set",
        "full_consent_code",
    )
    list_filter = (
        "study",
        "phs",
        "full_consent_code",
    )
    sortable_by = (
        "id",
        "workspace",
        "version",
    )
