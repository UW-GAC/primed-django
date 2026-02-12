"""Forms classes for the `cdsa` app."""

from anvil_consortium_manager.forms import Bootstrap5MediaFormMixin
from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError
from tree_queries.forms import TreeNodeMultipleChoiceField

from primed.primed_anvil.forms import CustomDateInput

from . import models


class AgreementMajorVersionIsValidForm(forms.ModelForm):
    class Meta:
        model = models.AgreementMajorVersion
        fields = ("is_valid",)
        widgets = {
            "is_valid": forms.HiddenInput,
        }


class SignedAgreementForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a SignedAgreement object."""

    version = forms.ModelChoiceField(queryset=models.AgreementVersion.objects.filter(major_version__is_valid=True))

    class Meta:
        model = models.SignedAgreement
        fields = (
            "cc_id",
            "representative",
            "representative_role",
            "signing_institution",
            "version",
            "date_signed",
            "accessors",
        )
        widgets = {
            "representative": autocomplete.ModelSelect2(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
            "date_signed": CustomDateInput(),
            "accessors": autocomplete.ModelSelect2Multiple(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }


class SignedAgreementStatusForm(forms.ModelForm):
    """Form to update the status of a SignedAgreement."""

    class Meta:
        model = models.SignedAgreement
        fields = ("status",)
        help_texts = {"status": """The status of this Signed Agreement."""}
        widgets = {"status": forms.RadioSelect}


class SignedAgreementAccessorsForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form to update accessors for `SignedAgreementAccessor` objects."""

    class Meta:
        model = models.SignedAgreement
        fields = ("accessors",)
        widgets = {
            "accessors": autocomplete.ModelSelect2Multiple(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }


class MemberAgreementForm(forms.ModelForm):
    is_primary = forms.TypedChoiceField(
        coerce=lambda x: x == "True",
        choices=((True, "Primary"), (False, "Component")),
        widget=forms.RadioSelect,
        label="Agreement type",
    )

    class Meta:
        model = models.MemberAgreement
        fields = (
            "signed_agreement",
            "study_site",
            "is_primary",
        )

    def clean(self):
        """Custom checks:

        - the study_site associated with the MemberAgreement should match one of the study sites of the representative.
        - the representative should be an active user.
        """
        cleaned_data = super().clean()
        study_site = cleaned_data.get("study_site")
        signed_agreement = cleaned_data.get("signed_agreement")

        if not signed_agreement:
            return cleaned_data

        representative = signed_agreement.representative

        # Check if representative is an active user
        if representative and not representative.is_active:
            raise ValidationError("The representative must be an active user.")

        if study_site and representative:
            if not representative.study_sites.exists():
                return cleaned_data

            # Check if study_site is one of representative's study_sites
            if study_site not in representative.study_sites.all():
                raise ValidationError("The study site must be one of the representative's study sites.")

        return cleaned_data


class DataAffiliateAgreementForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    is_primary = forms.TypedChoiceField(
        coerce=lambda x: x == "True",
        choices=((True, "Primary"), (False, "Component")),
        widget=forms.RadioSelect,
        label="Agreement type",
    )

    class Meta:
        model = models.DataAffiliateAgreement
        fields = (
            "signed_agreement",
            "uploaders",
            "study",
            "is_primary",
            "additional_limitations",
            "requires_study_review",
        )
        widgets = {
            "study": autocomplete.ModelSelect2(
                url="primed_anvil:studies:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
            "uploaders": autocomplete.ModelSelect2Multiple(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }


class DataAffiliateAgreementUploadersForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form to update uploaders for `DataAffiliateAgreement` objects."""

    class Meta:
        model = models.DataAffiliateAgreement
        fields = ("uploaders",)
        widgets = {
            "uploaders": autocomplete.ModelSelect2Multiple(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }


class NonDataAffiliateAgreementForm(forms.ModelForm):
    class Meta:
        model = models.NonDataAffiliateAgreement
        fields = (
            "signed_agreement",
            "affiliation",
        )


class CDSAWorkspaceForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for `CDSAWorkspace` objects."""

    gsr_restricted = forms.TypedChoiceField(
        coerce=lambda x: x == "True",
        choices=((True, "Restricted"), (False, "Unrestricted")),
        widget=forms.RadioSelect,
        label="GSR restricted?",
        help_text="Indicator of whether public posting of GSRs is restricted.",
    )

    class Meta:
        model = models.CDSAWorkspace
        fields = (
            "requested_by",
            "study",
            "data_use_permission",
            "data_use_modifiers",
            "disease_term",
            "additional_limitations",
            "gsr_restricted",
            "acknowledgments",
            "available_data",
            "disease_term",
            "workspace",
        )
        widgets = {
            "study": autocomplete.ModelSelect2(
                url="primed_anvil:studies:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
            "data_use_modifiers": forms.CheckboxSelectMultiple,
            "requested_by": autocomplete.ModelSelect2(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
            "available_data": forms.CheckboxSelectMultiple,
        }
        field_classes = {
            "data_use_modifiers": TreeNodeMultipleChoiceField,
        }
        help_texts = {
            "data_use_modifiers": """The DataUseModifiers associated with this study-consent group.
            --- represents a child modifier."""
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Making location required
        self.fields["data_use_permission"].required = True
