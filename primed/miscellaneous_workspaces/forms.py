"""Forms for the `workspaces` app."""

from django import forms

from . import models


class SimulatedDataWorkspaceForm(forms.ModelForm):
    """Form for a SimulatedDataWorkspace object."""

    class Meta:
        model = models.SimulatedDataWorkspace
        fields = ("workspace",)


class ConsortiumDevelWorkspaceForm(forms.ModelForm):
    """Form for a ConsortiumDevelWorkspace object."""

    class Meta:
        model = models.ConsortiumDevelWorkspace
        fields = ("workspace",)


class ExampleWorkspaceForm(forms.ModelForm):
    """Form for a ExampleWorkspace object."""

    class Meta:
        model = models.ExampleWorkspace
        fields = ("workspace",)
