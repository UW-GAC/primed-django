from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from . import models


@admin.register(models.SimulatedDataWorkspace)
class SimulatedDataWorkspaceAdmin(SimpleHistoryAdmin):
    """Admin class for the `SimulatedDataWorkspace` model."""

    list_display = ("workspace",)


@admin.register(models.ConsortiumDevelWorkspace)
class ConsortiumDevelWorkspaceAdmin(SimpleHistoryAdmin):
    """Admin class for the `ConsortiumDevelWorkspace` model."""

    list_display = ("workspace",)


@admin.register(models.ResourceWorkspace)
class ResourceWorkspaceAdmin(SimpleHistoryAdmin):
    """Admin class for the `ResourceWorkspace` model."""

    list_display = ("workspace",)


@admin.register(models.TemplateWorkspace)
class TemplateWorkspaceAdmin(SimpleHistoryAdmin):
    """Admin class for the `TemplateWorkspace` model."""

    list_display = ("workspace",)


@admin.register(models.OpenAccessWorkspace)
class OpenAccessWorkspaceAdmin(SimpleHistoryAdmin):
    """Admin class for the `OpenAccessWorkspace` model."""

    list_display = ("workspace",)


@admin.register(models.DataPrepWorkspace)
class DataPrepWorkspaceAdmin(SimpleHistoryAdmin):
    """Admin class for the `DataPrepWorkspace` model."""

    list_display = (
        "workspace",
        "is_active",
    )
    list_filter = ("is_active",)
