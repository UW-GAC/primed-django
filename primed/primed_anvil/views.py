from anvil_consortium_manager.auth import AnVILConsortiumManagerViewRequired
from dal import autocomplete
from django.db.models import Q
from django.views.generic import DetailView
from django_tables2 import SingleTableView

from . import models, tables


class StudyDetail(AnVILConsortiumManagerViewRequired, DetailView):
    """View to show details about a `Study`."""

    model = models.Study


class StudyList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """View to show a list of `Study`s."""

    model = models.Study
    table_class = tables.StudyTable


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
