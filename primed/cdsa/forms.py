from anvil_consortium_manager.forms import Bootstrap5MediaFormMixin
from django import forms

from . import models


class CDSAForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a CDSA object."""

    class Meta:
        model = models.CDSA
        fields = (
            "cc_id",
            "representative",
            "instutition",
            "type",
            "is_component",
            "group",
            "representatitive_role",
        )
        widgets = {"type": forms.RadioSelect}
