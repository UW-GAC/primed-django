from anvil_consortium_manager.auth import AnVILConsortiumManagerViewRequired
from django.http import Http404
from django.views.generic import DetailView, TemplateView

from . import models


class MPTTTreeMixin:
    """Mixin to help display an MPTT tree."""

    title = None
    model = None
    template_name = "duo/mptt_tree.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["title"] = self.title
        context["nodes"] = self.model.objects.all()
        return context


class DataUsePermissionList(
    AnVILConsortiumManagerViewRequired, MPTTTreeMixin, TemplateView
):

    title = "DUO Data Use Permission tree"
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


class DataUseModifierList(
    AnVILConsortiumManagerViewRequired, MPTTTreeMixin, TemplateView
):

    title = "DUO Data Use Modifier tree"
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
