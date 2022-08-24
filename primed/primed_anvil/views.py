from anvil_consortium_manager.auth import AnVILConsortiumManagerViewRequired
from django.views.generic import DetailView
from django_tables2 import SingleTableView

from . import models, tables


class StudyDetail(AnVILConsortiumManagerViewRequired, DetailView):
    """View to show details about a `Study`."""

    model = models.Study


class StudyList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """View to a list of `Study`s."""

    model = models.Study
    table_class = tables.StudyTable
