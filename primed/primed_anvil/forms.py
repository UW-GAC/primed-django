from dal import autocomplete
from django import forms
from django.contrib.auth import get_user_model


class CustomDateInput(forms.widgets.DateInput):
    """Form widget to select a date with a calendar picker."""

    input_type = "date"


class UserSearchForm(forms.ModelForm):
    """Form for the user search"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = True

    class Meta:
        model = get_user_model()
        fields = ("name",)

        widgets = {
            "name": autocomplete.ListSelect2(
                url="gregor_anvil:user:autocomplete",
                attrs={"data-theme": "bootstrap-5"},
            ),
        }

        help_texts = {
            "name": "Enter either the name or username to search",
        }
