"""Tables for the `miscellaneous_workspace` app."""

import django_tables2 as tables
from anvil_consortium_manager.models import Workspace

from primed.primed_anvil.tables import (
    BooleanIconColumn,
    WorkspaceSharedWithConsortiumColumn,
)


class OpenAccessWorkspaceUserTable(tables.Table):
    """Class to render a table of Workspace objects with OpenAccessWorkspace workspace data."""

    name = tables.columns.Column(linkify=True)
    is_shared = WorkspaceSharedWithConsortiumColumn()
    openaccessworkspace__studies = tables.ManyToManyColumn(
        linkify_item=True,
    )

    class Meta:
        model = Workspace
        fields = (
            "name",
            "openaccessworkspace__studies",
            "is_shared",
        )
        order_by = ("name",)


class OpenAccessWorkspaceStaffTable(OpenAccessWorkspaceUserTable):
    """Class to render a table of Workspace objects with OpenAccessWorkspace workspace data."""

    billing_project = tables.Column(linkify=True)

    class Meta:
        model = Workspace
        fields = (
            "name",
            "billing_project",
            "openaccessworkspace__studies",
            "is_shared",
        )
        order_by = ("name",)


class DataPrepWorkspaceUserTable(tables.Table):
    """Class to render a table of Workspace objects with DataPrepWorkspace workspace data."""

    name = tables.columns.Column(linkify=True)
    dataprepworkspace__target_workspace__name = tables.columns.Column(linkify=True, verbose_name="Target workspace")
    dataprepworkspace__is_active = BooleanIconColumn(verbose_name="Active?", show_false_icon=True)

    class Meta:
        model = Workspace
        fields = (
            "name",
            "dataprepworkspace__target_workspace__name",
            "dataprepworkspace__is_active",
        )
        order_by = ("name",)


class DataPrepWorkspaceStaffTable(DataPrepWorkspaceUserTable):
    """Class to render a table of Workspace objects with DataPrepWorkspace workspace data."""

    billing_project = tables.columns.Column(linkify=True)

    class Meta:
        model = Workspace
        fields = (
            "name",
            "billing_project",
            "dataprepworkspace__target_workspace__name",
            "dataprepworkspace__is_active",
        )
        order_by = ("name",)
