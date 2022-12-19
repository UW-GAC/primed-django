from anvil_consortium_manager.auth import AnVILConsortiumManagerViewRequired
from django.http import Http404
from django.views.generic import DetailView, ListView

from . import models


class DataUsePermissionList(AnVILConsortiumManagerViewRequired, ListView):

    model = models.DataUsePermission


class DataUsePermissionDetail(AnVILConsortiumManagerViewRequired, DetailView):

    model = models.DataUsePermission

    def get_object(self):
        try:
            obj = self.model.objects.get(identifier=self.kwargs.get("id"))
        except self.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": self.model._meta.verbose_name}
            )
        return obj


class DataUseModifierList(AnVILConsortiumManagerViewRequired, ListView):

    model = models.DataUseModifier


class DataUseModifierDetail(AnVILConsortiumManagerViewRequired, DetailView):

    model = models.DataUseModifier

    def get_object(self):
        try:
            obj = self.model.objects.get(identifier=self.kwargs.get("id"))
        except self.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": self.model._meta.verbose_name}
            )
        return obj
