from anvil_consortium_manager.auth import AnVILConsortiumManagerViewRequired
from django.views.generic import DetailView
from django_tables2 import SingleTableMixin

from . import models, tables


class dbGaPStudyDetail(
    AnVILConsortiumManagerViewRequired, SingleTableMixin, DetailView
):
    """View to show details about a `dbGaPStudy`."""

    model = models.dbGaPStudy
    table_class = tables.dbGaPWorkspaceTable
    context_table_name = "workspace_table"

    def get_table_data(self):
        return self.object.dbgapworkspace_set.all()
