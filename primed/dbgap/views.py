from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerEditRequired,
    AnVILConsortiumManagerViewRequired,
)
from anvil_consortium_manager.models import Workspace
from anvil_consortium_manager.views import SuccessMessageMixin
from django.views.generic import CreateView, DetailView
from django_tables2 import SingleTableMixin, SingleTableView

from . import forms, models, tables


class dbGaPStudyDetail(
    AnVILConsortiumManagerViewRequired, SingleTableMixin, DetailView
):
    """View to show details about a `dbGaPStudy`."""

    model = models.dbGaPStudy
    context_table_name = "workspace_table"

    def get_table(self):
        return tables.dbGaPWorkspaceTable(
            Workspace.objects.filter(dbgapworkspace__dbgap_study=self.object),
            exclude=(
                "dbgapworkspace__dbgap_study__study",
                "dbgapworkspace__dbgap_study__phs",
            ),
        )


class dbGaPStudyList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """View to show a list of dbGaPStudy objects."""

    model = models.dbGaPStudy
    table_class = tables.dbGaPStudyTable


class dbGaPStudyCreate(
    AnVILConsortiumManagerEditRequired, SuccessMessageMixin, CreateView
):
    """View to create a new dbGaPStudy."""

    model = models.dbGaPStudy
    form_class = forms.dbGaPStudyForm
    success_msg = "dbGaP Study successfully created."
