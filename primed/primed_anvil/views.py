from anvil_consortium_manager.auth import AnVILConsortiumManagerViewRequired
from django.views.generic import DetailView

from . import models

# from django_tables2 import SingleTableView


class StudyDetail(AnVILConsortiumManagerViewRequired, DetailView):
    """View to show details about a `Study`."""

    model = models.Study
