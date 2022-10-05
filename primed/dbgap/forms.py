"""Forms classes for the `dbgap` app."""

import jsonschema
from django import forms
from django.core.exceptions import ValidationError

from . import constants, models


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


class dbGaPDataAccessRequestFromJsonForm(forms.Form):
    """Create dbGaP data access requests from JSON data."""

    json = forms.JSONField()
    ERROR_JSON_VALIDATION = "JSON validation error: %(error)s"

    def clean_json(self):
        data = self.cleaned_data["json"]
        try:
            jsonschema.validate(data, constants.json_dar_schema)
        except jsonschema.exceptions.ValidationError as e:
            # Replace the full json string because it will be very long
            error_message = e.message.replace(str(e.instance), "JSON array")
            raise ValidationError(
                self.ERROR_JSON_VALIDATION, params={"error": error_message}
            )
        return data
