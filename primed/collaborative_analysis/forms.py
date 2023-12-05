from anvil_consortium_manager.forms import Bootstrap5MediaFormMixin
from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError

from . import models


class CollaborativeAnalysisWorkspaceForm(Bootstrap5MediaFormMixin, forms.ModelForm):
    """Form for a dbGaPWorkspace object."""

    class Meta:
        model = models.CollaborativeAnalysisWorkspace
        fields = (
            "purpose",
            "proposal_id",
            "source_workspaces",
            "custodian",
            "workspace",
        )
        widgets = {
            "source_workspaces": autocomplete.ModelSelect2Multiple(
                url="anvil_consortium_manager:workspaces:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
            "custodian": autocomplete.ModelSelect2(
                url="users:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }
        #     "data_use_modifiers": forms.CheckboxSelectMultiple,
        #     "requested_by": autocomplete.ModelSelect2(
        #         url="users:autocomplete",
        #         attrs={"data-theme": "bootstrap-5"},
        #     ),
        #     "available_data": forms.CheckboxSelectMultiple,
        # }
        # help_texts = {
        #     "data_use_modifiers": """The DataUseModifiers associated with this study-consent group.
        #     --- represents a child modifier."""
        # }

    def clean(self):
        """Custom checks:

        - workspace and source_workspace are different.
        """
        cleaned_data = super().clean()

        # Workspace is not also a source_workspace.
        workspace = cleaned_data.get("workspace", None)
        source_workspaces = cleaned_data.get("source_workspaces", [])
        if workspace and source_workspaces:
            if workspace in source_workspaces:
                raise ValidationError("source_workspaces cannot include workspace.")

        return cleaned_data
