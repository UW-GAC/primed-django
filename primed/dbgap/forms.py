"""Forms classes for the `dbgap` app."""

from django import forms

from . import models


class dbGaPStudyForm(forms.ModelForm):
    """Form for a dbGaPStudy object."""

    class Meta:
        model = models.dbGaPStudy
        fields = (
            "phs",
            "study",
        )


class dbGaPWorkspaceForm(forms.ModelForm):
    """Form for a dbGaPWorkspace object."""

    class Meta:
        model = models.dbGaPWorkspace
        fields = (
            "dbgap_study",
            "dbgap_version",
            "dbgap_participant_set",
            "full_consent_code",
            "data_use_limitations",
            "data_use_permission",
            "disease_restriction",
            "data_use_modifiers",
            "workspace",
        )
