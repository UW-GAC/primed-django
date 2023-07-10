from django import forms


class CustomDateInput(forms.widgets.DateInput):
    """Form widget to select a date with a calendar picker."""

    input_type = "date"
