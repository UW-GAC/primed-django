"""Tables for the `miscellaneous_workspace` app."""

import django_tables2 as tables
from anvil_consortium_manager.models import Workspace

from primed.primed_anvil.tables import WorkspaceSharedWithConsortiumColumn


class OpenAccessWorkspaceTable(tables.Table):
    """Class to render a table of Workspace objects with OpenAccessWorkspace workspace data."""

    name = tables.columns.Column(linkify=True)
    billing_project = tables.Column(linkify=True)
    is_shared = WorkspaceSharedWithConsortiumColumn()

    class Meta:
        model = Workspace
        fields = (
            "name",
            "billing_project",
            "openaccessworkspace__studies",
            "is_shared",
        )
        order_by = ("name",)


class OpenAccessWorkspaceLimitedViewTable(tables.Table):
    """Class to render a table of Workspace objects with OpenAccessWorkspace workspace data."""

    name = tables.columns.Column()
    billing_project = tables.Column()
    is_shared = WorkspaceSharedWithConsortiumColumn()

    class Meta:
        model = Workspace
        fields = (
            "name",
            "billing_project",
            "openaccessworkspace__studies",
            "is_shared",
        )
        order_by = ("name",)
