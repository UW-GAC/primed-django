from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from . import models


@admin.register(models.SimulatedDataWorkspace)
class SimulatedDataWorkspaceAdmin(SimpleHistoryAdmin):
    """Admin class for the `SimulatedDataWorkspace` model."""

    list_display = ("workspace",)
