import django_tables2 as tables
from anvil_consortium_manager.models import Workspace


class CollaborativeAnalysisWorkspaceUserTable(tables.Table):
    """Class to render a table of Workspace objects with CollaborativeAnalysisWorkspace data."""

    name = tables.columns.Column(linkify=True)
    number_source_workspaces = tables.columns.Column(
        accessor="pk",
        verbose_name="Number of source workspaces",
        orderable=False,
    )

    class Meta:
        model = Workspace
        fields = (
            "name",
            "collaborativeanalysisworkspace__custodian",
            "number_source_workspaces",
        )
        order_by = ("name",)

    def render_number_source_workspaces(self, record):
        """Render the number of source workspaces."""
        return record.collaborativeanalysisworkspace.source_workspaces.count()


class CollaborativeAnalysisWorkspaceStaffTable(CollaborativeAnalysisWorkspaceUserTable):
    """Class to render a table of Workspace objects with CollaborativeAnalysisWorkspace data."""

    name = tables.columns.Column(linkify=True)
    billing_project = tables.Column(linkify=True)
    collaborativeanalysisworkspace__custodian = tables.Column(linkify=True)

    class Meta:
        model = Workspace
        fields = (
            "name",
            "billing_project",
            "collaborativeanalysisworkspace__custodian",
            "number_source_workspaces",
        )
        order_by = ("name",)
