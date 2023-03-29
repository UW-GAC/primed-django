from anvil_consortium_manager.anvil_api import AnVILAPIError
from anvil_consortium_manager.auth import AnVILConsortiumManagerEditRequired
from anvil_consortium_manager.models import ManagedGroup
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.views.generic import CreateView

from . import forms, models


class CDSACreate(AnVILConsortiumManagerEditRequired, SuccessMessageMixin, CreateView):
    """View to create a new CDSA."""

    model = models.CDSA
    form_class = forms.CDSAForm
    success_message = "CDSA successfully created."
    ERROR_CREATING_GROUP = "Error creating Managed Group in app."

    # @transaction.atomic
    def form_valid(self, form):
        """Create a managed group in the app on AnVIL and link it to this application."""
        cc_id = form.cleaned_data["cc_id"]
        group_name = "{}_{}".format("TEST", cc_id)
        managed_group = ManagedGroup(name=group_name)
        try:
            managed_group.full_clean()
        except ValidationError:
            messages.add_message(
                self.request, messages.ERROR, self.ERROR_CREATING_GROUP
            )
            return self.render_to_response(self.get_context_data(form=form))
        try:
            managed_group.anvil_create()
        except AnVILAPIError as e:
            messages.add_message(
                self.request, messages.ERROR, "AnVIL API Error: " + str(e)
            )
            return self.render_to_response(self.get_context_data(form=form))
        managed_group.save()
        form.instance.anvil_access_group = managed_group
        return super().form_valid(form)
