"""Forms for the `workspaces` app."""

from anvil_consortium_manager.forms import Bootstrap5MediaFormMixin
from dal import autocomplete
from django import forms

from . import models


class SimulatedDataWorkspaceForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a SimulatedDataWorkspace object."""

    class Meta:
        model = models.SimulatedDataWorkspace
        fields = (
            "workspace",
            "requested_by",
        )
        widgets = {
            "requested_by": autocomplete.ModelSelect2(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }


class ConsortiumDevelWorkspaceForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a ConsortiumDevelWorkspace object."""

    class Meta:
        model = models.ConsortiumDevelWorkspace
        fields = (
            "workspace",
            "requested_by",
        )
        widgets = {
            "requested_by": autocomplete.ModelSelect2(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }


class ResourceWorkspaceForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a ResourceWorkspace object."""

    class Meta:
        model = models.ResourceWorkspace
        fields = (
            "workspace",
            "requested_by",
        )
        widgets = {
            "requested_by": autocomplete.ModelSelect2(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }


class TemplateWorkspaceForm(forms.ModelForm):
    """Form for a TemplateWorkspace object."""

    class Meta:
        model = models.TemplateWorkspace
        fields = (
            "workspace",
            "intended_usage",
        )


class OpenAccessWorkspaceForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a OpenAccessWorkspace object."""

    data_url = forms.URLField(max_length=255, assume_scheme="https")

    class Meta:
        model = models.OpenAccessWorkspace
        fields = (
            "workspace",
            "requested_by",
            "studies",
            "data_source",
            "data_url",
            "available_data",
        )
        widgets = {
            "studies": autocomplete.ModelSelect2Multiple(
                url="primed_anvil:studies:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
            "requested_by": autocomplete.ModelSelect2(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
            "available_data": forms.CheckboxSelectMultiple,
        }


class DataPrepWorkspaceForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a DataPrepWorkspace object."""

    class Meta:
        model = models.DataPrepWorkspace
        fields = (
            "workspace",
            "target_workspace",
            "requested_by",
            "is_active",
        )
        widgets = {
            "target_workspace": autocomplete.ModelSelect2(
                url="anvil_consortium_manager:workspaces:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
            "requested_by": autocomplete.ModelSelect2(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }
