from anvil_consortium_manager.forms import WorkspaceForm
from django import forms


class CustomDateInput(forms.widgets.DateInput):
    """Form widget to select a date with a calendar picker."""

    input_type = "date"


class WorkspaceAuthDomainDisabledForm(WorkspaceForm):
    """Form for creating a workspace with the authorization domains field disabled."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "authorization_domains" in self.fields:
            self.fields["authorization_domains"].disabled = True
            self.fields["authorization_domains"].help_text = (
                "An authorization domain will be automatically created " "using the name of the workspace."
            )
