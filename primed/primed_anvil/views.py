from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerEditRequired,
    AnVILConsortiumManagerViewRequired,
)
from anvil_consortium_manager.models import Workspace
from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.views.generic import CreateView, DetailView, TemplateView
from django_tables2 import SingleTableMixin, SingleTableView

from primed.dbgap.tables import dbGaPWorkspaceTable
from primed.users.tables import UserTable

from . import helpers, models, tables

User = get_user_model()


class StudyDetail(AnVILConsortiumManagerViewRequired, SingleTableMixin, DetailView):
    """View to show details about a `Study`."""

    model = models.Study
    table_class = dbGaPWorkspaceTable
    context_table_name = "dbgap_workspace_table"

    def get_table_data(self):
        return Workspace.objects.filter(
            dbgapworkspace__dbgap_study_accession__studies=self.object
        )


class StudyList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """View to show a list of `Study`s."""

    model = models.Study
    table_class = tables.StudyTable


class StudyCreate(AnVILConsortiumManagerEditRequired, SuccessMessageMixin, CreateView):
    """View to create a new `Study`."""

    model = models.Study
    fields = ("short_name", "full_name")
    success_message = "Study successfully created."

    def get_success_url(self):
        return self.object.get_absolute_url()


class StudyAutocomplete(
    AnVILConsortiumManagerViewRequired, autocomplete.Select2QuerySetView
):
    """View to provide autocompletion for `Study`s. Match either the `short_name` or `full_name`."""

    def get_result_label(self, result):
        s = "{} ({})".format(result.full_name, result.short_name)
        print(s)
        return s

    def get_selected_result_label(self, result):
        return str(result)

    def get_queryset(self):
        # Only active accounts.
        qs = models.Study.objects.order_by("short_name")

        if self.q:
            qs = qs.filter(
                Q(short_name__icontains=self.q) | Q(full_name__icontains=self.q)
            )

        return qs


class StudySiteDetail(AnVILConsortiumManagerViewRequired, SingleTableMixin, DetailView):
    """View to show details about a `StudySite`."""

    model = models.StudySite
    context_table_name = "site_user_table"

    def get_table(self):
        return UserTable(User.objects.filter(study_sites=self.object))


class StudySiteList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """View to show a list of `StudySite`s."""

    model = models.StudySite
    table_class = tables.StudySiteTable


class AvailableDataList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """View to show a list of `AvailableData`."""

    model = models.AvailableData
    table_class = tables.AvailableDataTable


class AvailableDataDetail(
    AnVILConsortiumManagerViewRequired, SingleTableMixin, DetailView
):
    """View to show details about a `AvailableData`."""

    model = models.AvailableData
    context_table_name = "dbgap_workspace_table"
    table_class = dbGaPWorkspaceTable
    context_table_name = "dbgap_workspace_table"

    def get_table_data(self):
        return Workspace.objects.filter(dbgapworkspace__available_data=self.object)


class DataSummaryView(LoginRequiredMixin, TemplateView):

    template_name = "primed_anvil/data_summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table_data = helpers.get_summary_table_data()
        context["summary_table"] = tables.DataSummaryTable(table_data)
        return context
