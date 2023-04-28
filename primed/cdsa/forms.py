"""Forms classes for the `cdsa` app."""

from anvil_consortium_manager.forms import Bootstrap5MediaFormMixin
from dal import autocomplete
from django import forms

from . import models


# I forget why I had to code this for PRIMED but I did.
class CustomDateInput(forms.widgets.DateInput):
    """Form input field to display a date with a calendar picker."""

    input_type = "date"


class SignedAgreementForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a SignedAgreement object."""

    is_primary = forms.BooleanField(
        widget=forms.RadioSelect(choices=[(True, "Primary"), (False, "Component")]),
        required=True,
        label="Agreement type",
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
        }


class MemberAgreementForm(forms.ModelForm):
    class Meta:
        model = models.MemberAgreement
        fields = (
            "signed_agreement",
            "study_site",
        )


MemberAgreementInlineFormset = forms.inlineformset_factory(
    models.SignedAgreement,
    models.MemberAgreement,
    form=MemberAgreementForm,
    can_delete=False,
    extra=1,
    min_num=1,
    max_num=1,
)


class DataAffiliateAgreementForm(forms.ModelForm):
    class Meta:
        model = models.DataAffiliateAgreement
        fields = (
            "signed_agreement",
            "study",
        )


DataAffiliateAgreementInlineFormset = forms.inlineformset_factory(
    models.SignedAgreement,
    models.DataAffiliateAgreement,
    form=DataAffiliateAgreementForm,
    can_delete=False,
    extra=1,
    min_num=1,
    max_num=1,
)


class NonDataAffiliateAgreementForm(forms.ModelForm):
    class Meta:
        model = models.NonDataAffiliateAgreement
        fields = (
            "signed_agreement",
            "affiliation",
        )


NonDataAffiliateAgreementInlineFormset = forms.inlineformset_factory(
    models.SignedAgreement,
    models.NonDataAffiliateAgreement,
    form=NonDataAffiliateAgreementForm,
    can_delete=False,
    extra=1,
    min_num=1,
    max_num=1,
)
