from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerEditRequired,
    AnVILConsortiumManagerViewRequired,
)
from anvil_consortium_manager.models import Workspace
from anvil_consortium_manager.views import SuccessMessageMixin
from dal import autocomplete
from django.db.models import Q
from django.views.generic import CreateView, DetailView
from django_tables2 import SingleTableMixin, SingleTableView

from primed.dbgap.tables import dbGaPWorkspaceTable

from . import models, tables


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
    success_msg = "Study successfully created."

    def get_success_url(self):
        return self.object.get_absolute_url()


class StudyAutocomplete(
    AnVILConsortiumManagerViewRequired, autocomplete.Select2QuerySetView
):
    """View to provide autocompletion for `Study`s. Match either the `short_name` or `full_name`."""

    def get_queryset(self):
        # Only active accounts.
        qs = models.Study.objects.order_by("short_name")

        if self.q:
            qs = qs.filter(
                Q(short_name__icontains=self.q) | Q(full_name__icontains=self.q)
            )

        return qs


class StudySiteDetail(AnVILConsortiumManagerViewRequired, DetailView):
    """View to show details about a `StudySite`."""

    model = models.StudySite


class StudySiteList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """View to show a list of `StudySite`s."""

    model = models.StudySite
    table_class = tables.StudySiteTable


class AvailableDataList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """View to show a list of `AvailableData`."""

    model = models.AvailableData
    table_class = tables.AvailableDataTable
