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
            "dbgap_project_id",
        )


# TODO: rename to dbGaPDataAccessSnapshotForm.
class dbGaPDataAccessJSONForm(forms.ModelForm):
    """Create a dbGaP data access snapshot and DARs from JSON data."""

    ERROR_JSON_VALIDATION = "JSON validation error: %(error)s"

    class Meta:
        model = models.dbGaPDataAccessSnapshot
        fields = (
            "dbgap_application",
            "dbgap_dar_data",
        )
        widgets = {
            "dbgap_application": forms.HiddenInput(),
        }

    def clean_dbgap_dar_data(self):
        data = self.cleaned_data["dbgap_dar_data"]
        try:
            jsonschema.validate(data, constants.json_dar_schema)
        except jsonschema.exceptions.ValidationError as e:
            # Replace the full json string because it will be very long
            error_message = e.message.replace(str(e.instance), "JSON array")
            raise ValidationError(
                self.ERROR_JSON_VALIDATION, params={"error": error_message}
            )
        # Return the first object in the array, since people will be cutting and pasting
        # from the dbGaP interface. It returns an array with one object, and we want to
        # store only object.
        return data[0]
