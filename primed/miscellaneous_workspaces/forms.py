"""Forms for the `workspaces` app."""

from anvil_consortium_manager.adapters.workspace import workspace_adapter_registry
from django import forms

from . import models


class SimulatedDataWorkspaceForm(forms.ModelForm):
    """Form for a SimulatedDataWorkspace object."""

    class Meta:
        model = models.SimulatedDataWorkspace
        fields = (
            "workspace",
            "requested_by",
        )


class ConsortiumDevelWorkspaceForm(forms.ModelForm):
    """Form for a ConsortiumDevelWorkspace object."""

    class Meta:
        model = models.ConsortiumDevelWorkspace
        fields = (
            "workspace",
            "requested_by",
        )


class ExampleWorkspaceForm(forms.ModelForm):
    """Form for a ExampleWorkspace object."""

    class Meta:
        model = models.ExampleWorkspace
        fields = (
            "workspace",
            "requested_by",
        )


class TemplateWorkspaceForm(forms.ModelForm):
    """Form for a TemplateWorkspace object."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the intended_workspace_type options, excluding "template".
        workspace_type_choices = [
            (key, value)
            for key, value in workspace_adapter_registry.get_registered_names().items()
            if key != "template"
        ]
        self.fields["intended_workspace_type"] = forms.ChoiceField(
            choices=[("", "---------")] + workspace_type_choices
        )

    class Meta:
        model = models.TemplateWorkspace
        fields = (
            "workspace",
            "intended_workspace_type",
        )


class OpenAccessWorkspaceForm(forms.ModelForm):
    """Form for a OpenAccessWorkspace object."""

    class Meta:
        model = models.OpenAccessWorkspace
        fields = (
            "workspace",
            "requested_by",
            "studies",
            "data_source",
            "available_data",
        )
