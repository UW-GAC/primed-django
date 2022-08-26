"""Forms classes for the primed_anvil app."""

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
            "data_use_modifiers",
            "workspace",
        )

        widgets = {
            "study": autocomplete.ModelSelect2(
                url="primed_anvil:studies:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }
