from anvil_consortium_manager.adapters.workspace import BaseWorkspaceAdapter
from anvil_consortium_manager.forms import WorkspaceForm

from . import forms, models, tables


class CollaborativeAnalysisWorkspaceAdapter(BaseWorkspaceAdapter):
    """Adapter for CollaborativeAnalysisWorkspace."""

    type = "collab_analysis"
    name = "Collaborative Analysis workspace"
    description = "Workspaces used for collaborative analyses"
    list_table_class_staff_view = tables.CollaborativeAnalysisWorkspaceStaffTable
    list_table_class_view = tables.CollaborativeAnalysisWorkspaceUserTable
    workspace_form_class = WorkspaceForm
    workspace_data_model = models.CollaborativeAnalysisWorkspace
    workspace_data_form_class = forms.CollaborativeAnalysisWorkspaceForm
    workspace_detail_template_name = "collaborative_analysis/collaborativeanalysisworkspace_detail.html"
