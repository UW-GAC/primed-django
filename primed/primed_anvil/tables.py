import django_tables2 as tables
from anvil_consortium_manager.models import Workspace


class dbGaPWorkspaceTable(tables.Table):
    """A table for Workspaces that includes fields from dbGaPWorkspace."""

    name = tables.columns.Column(linkify=True)

    class Meta:
        model = Workspace
        fields = (
            "name",
            "dbgapworkspace__study_consent_group__study",
            "dbgapworkspace__study_consent_group__full_consent_code",
            "dbgapworkspace__phs",
            "dbgapworkspace__version",
        )
