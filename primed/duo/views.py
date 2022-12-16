from anvil_consortium_manager.auth import AnVILConsortiumManagerViewRequired
from django.views.generic import TemplateView

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


class DataUseModifierList(
    AnVILConsortiumManagerViewRequired, MPTTTreeMixin, TemplateView
):

    title = "DUO Data Use Modifier tree"
    model = models.DataUseModifier
