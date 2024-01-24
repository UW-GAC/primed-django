from anvil_consortium_manager.auth import AnVILConsortiumManagerStaffViewRequired
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from . import audit, models


# Create your views here.
class WorkspaceAudit(AnVILConsortiumManagerStaffViewRequired, DetailView):
    """View to show audit results for a `CollaborativeAnalysisWorkspace`."""

    model = models.CollaborativeAnalysisWorkspace
    template_name = "collaborative_analysis/collaborativeanalysisworkspace_audit.html"

    def get_object(self, queryset=None):
        """Return the object the view is displaying."""
        if queryset is None:
            queryset = self.get_queryset()
        # Filter the queryset based on kwargs.
        billing_project_slug = self.kwargs.get("billing_project_slug", None)
        workspace_slug = self.kwargs.get("workspace_slug", None)
        queryset = queryset.filter(
            workspace__billing_project__name=billing_project_slug,
            workspace__name=workspace_slug,
        )
        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(
                _("No %(verbose_name)s found matching the query")
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Run the audit
        data_access_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit(
            queryset=[self.object]
        )
        data_access_audit.run_audit()
        context["verified_table"] = data_access_audit.get_verified_table()
        context["errors_table"] = data_access_audit.get_errors_table()
        context["needs_action_table"] = data_access_audit.get_needs_action_table()
        context["data_access_audit"] = data_access_audit
        return context
