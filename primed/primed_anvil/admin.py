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


@admin.register(models.StudySite)
class StudySiteAdmin(admin.ModelAdmin):
    """Admin class for the `Study` model."""

    list_display = ("short_name", "full_name", "drupal_node_id")
    search_fields = ("short_name", "full_name", "drupal_node_id")
    sortable_by = ("short_name", "full_name", "drupal_node_id")


@admin.register(models.AvailableData)
class AvailableDataAdmin(admin.ModelAdmin):
    """Admin class for the `AvailableData` model."""

    list_display = ("name",)
    search_fields = ("name", "description")
    sortable_by = ("name",)
