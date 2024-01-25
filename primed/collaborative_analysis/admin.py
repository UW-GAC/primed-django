from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from . import models


@admin.register(models.CollaborativeAnalysisWorkspace)
class CollaborativeAnalysisWorkspaceAdmin(SimpleHistoryAdmin):
    """Admin class for the `CollaborativeAnalysisWorkspace` model."""

    list_display = (
        "id",
        "workspace",
        "custodian",
    )
    list_filter = ("proposal_id",)
    sortable_by = (
        "id",
        "workspace",
        "custodian",
    )
