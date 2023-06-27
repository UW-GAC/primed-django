from dal import autocomplete
from django import forms


class CustomDateInput(forms.widgets.DateInput):
    """Form widget to select a date with a calendar picker."""

    input_type = "date"


class UserSearchForm(forms.Form):
    """Form for the user search"""

    user = forms.CharField(
        widget=autocomplete.ListSelect2(
            url="primed_anvil:user:autocomplete",
            attrs={"data-theme": "bootstrap-5"},
        ),
        required=True,
        help_text="Enter either the name or username to search",
    )
