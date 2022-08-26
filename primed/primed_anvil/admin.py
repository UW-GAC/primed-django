from django.contrib import admin

from . import models


@admin.register(models.Study)
class StudyAdmin(admin.ModelAdmin):
    """Admin class for the `Study` model."""

    list_display = (
        "short_name",
        "full_name",
    )
    search_fields = (
        "short_name",
        "full_name",
    )
    sortable_by = (
        "short_name",
        "full_name",
    )


@admin.register(models.DataUsePermission)
class DataUsePermissionAdmin(admin.ModelAdmin):
    """Admin class for the `DataUsePermission` model."""

    list_display = (
        "code",
        "identifier",
        "description",
    )
    search_fields = (
        "code",
        "identifier",
        "description",
    )
    sortable_by = (
        "code",
        "identifier",
        "description",
    )


@admin.register(models.DataUseModifier)
class DataUseModifierAdmin(admin.ModelAdmin):
    """Admin class for the `DataUseModifier` model."""

    list_display = (
        "code",
        "identifier",
        "description",
    )
    search_fields = (
        "code",
        "identifier",
        "description",
    )
    sortable_by = (
        "code",
        "identifier",
        "description",
    )


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
