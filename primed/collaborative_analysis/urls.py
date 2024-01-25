from django.urls import include, path

from . import views

app_name = "collaborative_analysis"


collaborative_analysis_workspace_patterns = (
    [
        path(
            "audit/",
            views.WorkspaceAuditAll.as_view(),
            name="audit_all",
        ),
        path(
            "<slug:billing_project_slug>/<slug:workspace_slug>/audit/",
            views.WorkspaceAudit.as_view(),
            name="audit",
        ),
    ],
    "workspaces",
)

urlpatterns = [
    path("workspaces/", include(collaborative_analysis_workspace_patterns)),
]
