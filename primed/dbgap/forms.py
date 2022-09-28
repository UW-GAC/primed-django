"""Forms classes for the `dbgap` app."""

from dal import autocomplete
from django import forms

from . import models


class dbGaPWorkspaceForm(forms.ModelForm):
    """Form for a dbGaPWorkspace object."""

    class Meta:
        model = models.dbGaPWorkspace
        fields = (
            "study",
            "phs",
            "version",
            "participant_set",
            "full_consent_code",
            "data_use_limitations",
            "data_use_permission",
            "disease_restriction",
            "data_use_modifiers",
            "workspace",
        )

        widgets = {
            "study": autocomplete.ModelSelect2(
                url="primed_anvil:studies:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }
