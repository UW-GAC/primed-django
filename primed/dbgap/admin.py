from django.contrib import admin

from . import models


@admin.register(models.dbGaPStudyAccession)
class dbGaPStudyAccessionAdmin(admin.ModelAdmin):
    """Admin class for the `dbGaPStudyAccession` model."""

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
        "dbgap_study_accession",
        "dbgap_version",
        "dbgap_participant_set",
        "full_consent_code",
    )
    list_filter = (
        "dbgap_study_accession",
        "full_consent_code",
    )
    sortable_by = (
        "id",
        "workspace",
        "version",
    )


@admin.register(models.dbGaPApplication)
class dbGaPApplicationAdmin(admin.ModelAdmin):
    """Admin class for the `dbGaPApplication` model."""

    list_display = (
        "principal_investigator",
        "project_id",
    )
