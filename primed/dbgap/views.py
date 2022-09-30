from anvil_consortium_manager.auth import AnVILConsortiumManagerViewRequired
from django.views.generic import DetailView

from . import models


class dbGaPStudyDetail(AnVILConsortiumManagerViewRequired, DetailView):
    """View to show details about a `dbGaPStudy`."""

    model = models.dbGaPStudy
