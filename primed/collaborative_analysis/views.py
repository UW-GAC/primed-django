from anvil_consortium_manager.anvil_api import AnVILAPIError
from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerStaffEditRequired,
    AnVILConsortiumManagerStaffViewRequired,
)
from anvil_consortium_manager.models import (
    Account,
    GroupAccountMembership,
    GroupGroupMembership,
    ManagedGroup,
)
from django.contrib import messages
from django.db import transaction
from django.forms.forms import Form
from django.http import Http404, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, TemplateView

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


class WorkspaceAuditAll(AnVILConsortiumManagerStaffViewRequired, TemplateView):
    """View to show audit results for all `CollaborativeAnalysisWorkspace` objects."""

    template_name = (
        "collaborative_analysis/collaborativeanalysisworkspace_audit_all.html"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Run the audit
        data_access_audit = audit.CollaborativeAnalysisWorkspaceAccessAudit(
            queryset=models.CollaborativeAnalysisWorkspace.objects.all()
        )
        data_access_audit.run_audit()
        context["verified_table"] = data_access_audit.get_verified_table()
        context["errors_table"] = data_access_audit.get_errors_table()
        context["needs_action_table"] = data_access_audit.get_needs_action_table()
        context["data_access_audit"] = data_access_audit
        return context


class CollaborativeAnalysisAuditResolve(
    AnVILConsortiumManagerStaffEditRequired, FormView
):

    form_class = Form
    template_name = "collaborative_analysis/audit_resolve.html"
    htmx_success = """<i class="bi bi-check-circle-fill"></i> Handled!"""
    htmx_error = """<i class="bi bi-x-circle-fill"></i> Error!"""

    def get_collaborative_analysis_workspace(self):
        """Look up the CollaborativeAnalysisWorkspace by billing project and name."""
        # Filter the queryset based on kwargs.
        billing_project_slug = self.kwargs.get("billing_project_slug", None)
        workspace_slug = self.kwargs.get("workspace_slug", None)
        queryset = models.CollaborativeAnalysisWorkspace.objects.filter(
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

    def get_member(self):
        """Look up the member (account or group) by email."""
        email = self.kwargs.get(
            "member_email",
        )
        # Check for an account first.
        try:
            return Account.objects.get(email=email)
        except Account.DoesNotExist:
            pass
        # Then check for a managed group.
        try:
            return ManagedGroup.objects.get(email=email)
        except ManagedGroup.DoesNotExist:
            raise Http404(
                _("No %(verbose_name)s found matching the query")
                % {"verbose_name": "Account or ManagedGroup"}
            )

    def get_audit_result(self):
        instance = audit.CollaborativeAnalysisWorkspaceAccessAudit(
            queryset=models.CollaborativeAnalysisWorkspace.objects.filter(
                pk=self.collaborative_analysis_workspace.pk
            )
        )
        # No way to include a queryset of members at this point - need to call the sub method directly.
        if isinstance(self.member, Account):
            instance._audit_workspace_and_account(
                self.collaborative_analysis_workspace, self.member
            )
        else:
            instance._audit_workspace_and_group(
                self.collaborative_analysis_workspace, self.member
            )
        # Set to completed, because we are just running this one specific check.
        instance.completed = True
        return instance.get_all_results()[0]

    def get(self, request, *args, **kwargs):
        self.collaborative_analysis_workspace = (
            self.get_collaborative_analysis_workspace()
        )
        self.member = self.get_member()
        self.audit_result = self.get_audit_result()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.collaborative_analysis_workspace = (
            self.get_collaborative_analysis_workspace()
        )
        self.member = self.get_member()
        self.audit_result = self.get_audit_result()
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["collaborative_analysis_workspace"] = (
            self.collaborative_analysis_workspace
        )
        context["member"] = self.member
        context["audit_result"] = self.audit_result
        return context

    def get_success_url(self):
        return self.collaborative_analysis_workspace.get_absolute_url()

    def form_valid(self, form):
        auth_domain = (
            self.collaborative_analysis_workspace.workspace.authorization_domains.first()
        )
        # Handle the result.
        try:
            with transaction.atomic():
                if isinstance(self.audit_result, audit.GrantAccess):
                    # Add to workspace auth domain.
                    if isinstance(self.member, Account):
                        membership = GroupAccountMembership(
                            group=auth_domain,
                            account=self.member,
                            role=GroupAccountMembership.MEMBER,
                        )
                    elif isinstance(self.member, ManagedGroup):
                        membership = GroupGroupMembership(
                            parent_group=auth_domain,
                            child_group=self.member,
                            role=GroupGroupMembership.MEMBER,
                        )
                    membership.full_clean()
                    membership.save()
                    membership.anvil_create()
                elif isinstance(self.audit_result, audit.RemoveAccess):
                    # Remove from CDSA group.
                    if isinstance(self.member, Account):
                        membership = GroupAccountMembership.objects.get(
                            group=auth_domain,
                            account=self.member,
                            role=GroupAccountMembership.MEMBER,
                        )
                    elif isinstance(self.member, ManagedGroup):
                        membership = GroupGroupMembership.objects.get(
                            parent_group=auth_domain,
                            child_group=self.member,
                            role=GroupGroupMembership.MEMBER,
                        )
                    membership.delete()
                    membership.anvil_delete()
                else:
                    pass
        except AnVILAPIError as e:
            if self.request.htmx:
                return HttpResponse(self.htmx_error)
            else:
                messages.error(self.request, "AnVIL API Error: " + str(e))
                return super().form_invalid(form)
        # Otherwise, the audit resolution succeeded.
        if self.request.htmx:
            return HttpResponse(self.htmx_success)
        else:
            return super().form_valid(form)
