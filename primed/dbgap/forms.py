"""Forms classes for the `dbgap` app."""

from django import forms

from . import models


class dbGaPStudyAccessionForm(forms.ModelForm):
    """Form for a dbGaPStudyAccession object."""

    class Meta:
        model = models.dbGaPStudyAccession
        fields = (
            "phs",
            "study",
        )


class dbGaPWorkspaceForm(forms.ModelForm):
    """Form for a dbGaPWorkspace object."""

    class Meta:
        model = models.dbGaPWorkspace
        fields = (
            "dbgap_study_accession",
            "dbgap_version",
            "dbgap_participant_set",
            "dbgap_consent_abbreviation",
            "dbgap_consent_code",
            "data_use_limitations",
            "data_use_permission",
            "disease_restriction",
            "data_use_modifiers",
            "workspace",
        )


class dbGaPApplicationForm(forms.ModelForm):
    """Form for a dbGaPApplication."""

    class Meta:
        model = models.dbGaPApplication
        fields = (
            "principal_investigator",
            "project_id",
        )
