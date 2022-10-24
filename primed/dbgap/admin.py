from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from . import models


@admin.register(models.dbGaPStudyAccession)
class dbGaPStudyAccessionAdmin(SimpleHistoryAdmin):
    """Admin class for the `dbGaPStudyAccession` model."""

    list_display = (
        "study",
        "dbgap_phs",
    )
    search_fields = ("short_name",)
    sortable_by = (
        "short_name",
        "full_name",
    )


@admin.register(models.dbGaPWorkspace)
class dbGaPWorkspaceAdmin(SimpleHistoryAdmin):
    """Admin class for the `dbGaPWorkspace` model."""

    list_display = (
        "id",
        "workspace",
        "dbgap_study_accession",
        "dbgap_version",
        "dbgap_participant_set",
        "dbgap_consent_abbreviation",
    )
    list_filter = (
        "dbgap_study_accession",
        "dbgap_consent_abbreviation",
    )
    sortable_by = (
        "id",
        "workspace",
        "version",
    )


@admin.register(models.dbGaPApplication)
class dbGaPApplicationAdmin(SimpleHistoryAdmin):
    """Admin class for the `dbGaPApplication` model."""

    list_display = (
        "principal_investigator",
        "dbgap_project_id",
    )


@admin.register(models.dbGaPDataAccessSnapshot)
class dbGaPDataAccessSnapshotAdmin(SimpleHistoryAdmin):
    """Admin class for the `dbGaPDataAccessSnapshot` model."""

    list_display = (
        "dbgap_application",
        "created",
    )
    list_filter = ("dbgap_application",)


@admin.register(models.dbGaPDataAccessRequest)
class dbGaPDataAccessRequestAdmin(SimpleHistoryAdmin):
    """Admin class for the `dbGaPDataAccessRequest` model."""

    list_display = (
        "dbgap_dar_id",
        "dbgap_data_access_snapshot",
        "dbgap_phs",
        "original_version",
        "dbgap_consent_code",
        "dbgap_consent_abbreviation",
    )
    list_filter = ("dbgap_data_access_snapshot",)
