from anvil_consortium_manager.forms import Bootstrap5MediaFormMixin
from django import forms
from tree_queries.forms import TreeNodeMultipleChoiceField

from . import models


class CDSAForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a CDSA object."""

    class Meta:
        model = models.CDSA
        fields = (
            "cc_id",
            "representative",
            "institution",
            "type",
            "is_component",
            "group",
            "representatitive_role",
        )
        widgets = {"type": forms.RadioSelect}


class CDSAWorkspaceForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a CDSAWorkspace object."""

    class Meta:
        model = models.CDSAWorkspace
        fields = (
            "cdsa",
            "study",
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
            "data_use_modifiers": forms.CheckboxSelectMultiple,
            # "requested_by": autocomplete.ModelSelect2(
            #     url="users:autocomplete",
            #     attrs={"data-theme": "bootstrap-5"},
            # ),
            "available_data": forms.CheckboxSelectMultiple,
        }
        help_texts = {
            "data_use_modifiers": """The DataUseModifiers associated with this study-consent group.
            --- represents a child modifier."""
        }
        field_classes = {
            "data_use_modifiers": TreeNodeMultipleChoiceField,
        }
