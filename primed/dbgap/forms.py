"""Forms classes for the `dbgap` app."""

import jsonschema
from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError
from tree_queries.forms import TreeNodeMultipleChoiceField

from primed.primed_anvil.forms import Bootstrap5MediaFormMixin

from . import constants, models


class dbGaPStudyAccessionForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a dbGaPStudyAccession object."""

    class Meta:
        model = models.dbGaPStudyAccession
        fields = (
            "dbgap_phs",
            "studies",
        )
        widgets = {
            "studies": autocomplete.ModelSelect2Multiple(
                url="primed_anvil:studies:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }


class dbGaPWorkspaceForm(Bootstrap5MediaFormMixin, forms.ModelForm):
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
            "acknowledgments",
            "data_use_permission",
            "disease_term",
            "data_use_modifiers",
            "available_data",
            "workspace",
            "requested_by",
        )
        widgets = {
            "dbgap_study_accession": autocomplete.ModelSelect2(
                url="dbgap:dbgap_study_accessions:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
            "data_use_modifiers": forms.CheckboxSelectMultiple,
        }
        help_texts = {
            "data_use_modifiers": """The DataUseModifiers associated with this study-consent group.
            --- represents a child modifier."""
        }
        field_classes = {
            "data_use_modifiers": TreeNodeMultipleChoiceField,
        }


class dbGaPApplicationForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a dbGaPApplication."""

    class Meta:
        model = models.dbGaPApplication
        fields = (
            "principal_investigator",
            "dbgap_project_id",
        )
        widgets = {
            "principal_investigator": autocomplete.ModelSelect2(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }


class dbGaPDataAccessSnapshotForm(forms.ModelForm):
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
            jsonschema.validate(data, constants.JSON_DAR_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            # Replace the full json string because it will be very long
            error_message = e.message.replace(str(e.instance), "JSON array")
            raise ValidationError(
                self.ERROR_JSON_VALIDATION, params={"error": error_message}
            )
        # Verify that there is only one project in the json.
        if len(data) > 1:
            raise ValidationError("JSON array includes more than one project ID.")
        # Return the first object in the array, since people will be cutting and pasting
        # from the dbGaP interface. It returns an array with one object, and we want to
        # store only object.
        return data[0]


class dbGaPDataAccessSnapshotMultipleForm(forms.Form):
    """Form to create new dbGaPDataAccessSnapshots for multiple dbGaPApplications at once."""

    ERROR_PROJECT_ID_DOES_NOT_EXIST = (
        "dbGaP Application(s) for some project id(s) do not exist in app."
    )
    ERROR_JSON_VALIDATION = "JSON validation error: %(error)s"

    dbgap_dar_data = forms.JSONField()

    def clean_dbgap_dar_data(self):
        data = self.cleaned_data["dbgap_dar_data"]
        try:
            jsonschema.validate(data, constants.JSON_DAR_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            # Replace the full json string because it will be very long
            error_message = e.message.replace(str(e.instance), "JSON array")
            raise ValidationError(
                self.ERROR_JSON_VALIDATION, params={"error": error_message}
            )
        # Verify that all projects exist.
        missing_ids = []
        for project_json in data:
            project_id = project_json["Project_id"]
            if not models.dbGaPApplication.objects.filter(
                dbgap_project_id=project_id
            ).exists():
                missing_ids.append(str(project_id))
        if missing_ids:
            raise ValidationError(self.ERROR_PROJECT_ID_DOES_NOT_EXIST)
        return data
