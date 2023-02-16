"""Form classes for the `primed_anvil` app."""


class Bootstrap5MediaFormMixin:
    """Form Mixin defined to set required Media for select2-bootstrap-5-theme."""

    class Media:
        # Loading the select2-bootstrap-5-theme before the select2 css breaks the widget.
        # Therefore, we need to put the css for the select2-bootstrap-5-theme here.
        css = {
            "screen": (
                "https://cdnjs.cloudflare.com/ajax/libs/select2-bootstrap-5-theme/1.3.0/select2-bootstrap-5-theme.min.css",  # NOQA: E501
            )
        }
