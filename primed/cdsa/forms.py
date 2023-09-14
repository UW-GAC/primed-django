"""Forms classes for the `cdsa` app."""

from anvil_consortium_manager.forms import Bootstrap5MediaFormMixin
from dal import autocomplete
from django import forms
from tree_queries.forms import TreeNodeMultipleChoiceField

from primed.primed_anvil.forms import CustomDateInput

from . import models


class SignedAgreementForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a SignedAgreement object."""

    is_primary = forms.TypedChoiceField(
        coerce=lambda x: x == "True",
        choices=((True, "Primary"), (False, "Component")),
        widget=forms.RadioSelect,
        label="Agreement type",
    )
    version = forms.ModelChoiceField(
        queryset=models.AgreementVersion.objects.filter(major_version__is_valid=True)
    )

    class Meta:
        model = models.SignedAgreement
        fields = (
            "cc_id",
            "representative",
            "representative_role",
            "signing_institution",
            "version",
            "date_signed",
            "is_primary",
        )
        widgets = {
            "representative": autocomplete.ModelSelect2(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
            "date_signed": CustomDateInput(),
        }


class MemberAgreementForm(forms.ModelForm):
    class Meta:
        model = models.MemberAgreement
        fields = (
            "signed_agreement",
            "study_site",
        )


class DataAffiliateAgreementForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    class Meta:
        model = models.DataAffiliateAgreement
        fields = (
            "signed_agreement",
            "study",
        )
        widgets = {
            "study": autocomplete.ModelSelect2(
                url="primed_anvil:studies:autocomplete",
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

    class Meta:
        model = models.CDSAWorkspace
        fields = (
            "requested_by",
            "study",
            "data_use_permission",
            "data_use_modifiers",
            "disease_term",
            "data_use_limitations",
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
