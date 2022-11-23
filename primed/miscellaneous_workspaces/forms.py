"""Forms for the `workspaces` app."""

from django import forms

from . import models


class SimulatedDataWorkspaceForm(forms.ModelForm):
    """Form for a SimulatedDataWorkspace object."""

    class Meta:
        model = models.SimulatedDataWorkspace
        fields = ("workspace",)
