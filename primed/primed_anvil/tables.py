import django_tables2 as tables
from anvil_consortium_manager.models import Workspace

from . import models


class StudyTable(tables.Table):
    """A table for `Study`s."""

    short_name = tables.columns.Column(linkify=True)

    class Meta:
        model = models.Study
        fields = ("short_name", "full_name")


class dbGaPWorkspaceTable(tables.Table):
    """A table for Workspaces that includes fields from dbGaPWorkspace."""

    name = tables.columns.Column(linkify=True)
    dbgapworkspace__study = tables.columns.Column(linkify=True)

    class Meta:
        model = Workspace
        fields = (
            "name",
            "dbgapworkspace__study",
            "dbgapworkspace__phs",
            "dbgapworkspace__version",
            "dbgapworkspace__full_consent_code",
        )

    def render_dbgapworkspace__phs(self, value):
        return "phs{0:06d}".format(value)

    def render_dbgapworkspace__version(self, value):
        return "v{}".format(value)
