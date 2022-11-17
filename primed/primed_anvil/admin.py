from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from . import models


@admin.register(models.Study)
class StudyAdmin(SimpleHistoryAdmin):
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
class DataUsePermissionAdmin(SimpleHistoryAdmin):
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
class DataUseModifierAdmin(SimpleHistoryAdmin):
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
