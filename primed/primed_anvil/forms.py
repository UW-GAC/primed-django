"""Forms classes for the primed_anvil app."""

from django import forms

from . import models


class dbGaPWorkspaceForm(forms.ModelForm):
    """Form for a dbGaPWorkspace object."""

    class Meta:
        model = models.dbGaPWorkspace
        fields = (
            "study_consent_group",
            "phs",
            "version",
            "participant_set",
            "workspace",
        )
