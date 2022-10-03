from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerEditRequired,
    AnVILConsortiumManagerViewRequired,
)
from anvil_consortium_manager.models import Workspace
from anvil_consortium_manager.views import SuccessMessageMixin
from django.views.generic import CreateView, DetailView
from django_tables2 import SingleTableMixin, SingleTableView

from . import forms, models, tables


class dbGaPStudyAccessionDetail(
    AnVILConsortiumManagerViewRequired, SingleTableMixin, DetailView
):
    """View to show details about a `dbGaPStudyAccession`."""

    model = models.dbGaPStudyAccession
    context_table_name = "workspace_table"

    def get_table(self):
        return tables.dbGaPWorkspaceTable(
            Workspace.objects.filter(dbgapworkspace__dbgap_study_accession=self.object),
            exclude=(
                "dbgapworkspace__dbgap_study_accession__study",
                "dbgapworkspace__dbgap_study_accession__phs",
            ),
        )


class dbGaPStudyAccessionList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """View to show a list of dbGaPStudyAccession objects."""

    model = models.dbGaPStudyAccession
    table_class = tables.dbGaPStudyAccessionTable


class dbGaPStudyAccessionCreate(
    AnVILConsortiumManagerEditRequired, SuccessMessageMixin, CreateView
):
    """View to create a new dbGaPStudyAccession."""

    model = models.dbGaPStudyAccession
    form_class = forms.dbGaPStudyAccessionForm
    success_msg = "dbGaP study accession successfully created."


class dbGaPApplicationDetail(AnVILConsortiumManagerViewRequired, DetailView):
    """View to show details about a `dbGaPApplication`."""

    model = models.dbGaPApplication
