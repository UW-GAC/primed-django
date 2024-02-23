from django.urls import include, path

from . import views

app_name = "collaborative_analysis"


collaborative_analysis_audit_patterns = (
    [
        path(
            "",
            views.WorkspaceAuditAll.as_view(),
            name="all",
        ),
        path(
            "workspaces/<slug:billing_project_slug>/<slug:workspace_slug>/",
            views.WorkspaceAudit.as_view(),
            name="workspaces",
        ),
    ],
    "audit",
)

urlpatterns = [
    path("audit/", include(collaborative_analysis_audit_patterns)),
]
