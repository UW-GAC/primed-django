from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerEditRequired,
    AnVILConsortiumManagerViewRequired,
)
from anvil_consortium_manager.models import Workspace
from anvil_consortium_manager.views import SuccessMessageMixin
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.views.generic import CreateView, DetailView, FormView
from django_tables2 import SingleTableMixin, SingleTableView

from . import forms, models, tables


class dbGaPStudyAccessionDetail(
    AnVILConsortiumManagerViewRequired, SingleTableMixin, DetailView
):
    """View to show details about a `dbGaPStudyAccession`."""

    model = models.dbGaPStudyAccession
    context_table_name = "workspace_table"

    def get_table(self):
        return tables.dbGaPWorkspaceTable(
            Workspace.objects.filter(dbgapworkspace__dbgap_study_accession=self.object),
            exclude=(
                "dbgapworkspace__dbgap_study_accession__study",
                "dbgapworkspace__dbgap_study_accession__phs",
            ),
        )


class dbGaPStudyAccessionList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """View to show a list of dbGaPStudyAccession objects."""

    model = models.dbGaPStudyAccession
    table_class = tables.dbGaPStudyAccessionTable


class dbGaPStudyAccessionCreate(
    AnVILConsortiumManagerEditRequired, SuccessMessageMixin, CreateView
):
    """View to create a new dbGaPStudyAccession."""

    model = models.dbGaPStudyAccession
    form_class = forms.dbGaPStudyAccessionForm
    success_msg = "dbGaP study accession successfully created."


class dbGaPApplicationDetail(
    AnVILConsortiumManagerViewRequired, SingleTableMixin, DetailView
):
    """View to show details about a `dbGaPApplication`."""

    model = models.dbGaPApplication
    context_table_name = "data_access_request_table"

    def get_table(self):
        return tables.dbGaPDataAccessRequestTable(
            self.object.dbgapdataaccessrequest_set.all(),
        )


class dbGaPApplicationList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """View to show a list of dbGaPApplication objects."""

    model = models.dbGaPApplication
    table_class = tables.dbGaPApplicationTable


class dbGaPApplicationCreate(
    AnVILConsortiumManagerEditRequired, SuccessMessageMixin, CreateView
):
    """View to create a new dbGaPApplication."""

    model = models.dbGaPApplication
    form_class = forms.dbGaPApplicationForm
    success_msg = "dbGaP application successfully created."


class dbGaPDataAccessRequestCreateFromJson(
    AnVILConsortiumManagerEditRequired, SuccessMessageMixin, FormView
):

    form_class = forms.dbGaPDataAccessRequestFromJsonForm
    template_name = "dbgap/dbgapdataaccessrequest_json_form.html"
    ERROR_DARS_ALREADY_ADDED = (
        "Data Access Requests have already been added for this application."
    )
    ERROR_PROJECT_ID_DOES_NOT_MATCH = (
        "Project id in JSON does not match dbGaP application project id."
    )
    ERROR_STUDY_ACCESSION_NOT_FOUND = "Study accession(s) not found in app."
    success_msg = "Successfully added Data Access Requests for this dbGaP application."

    def get(self, request, *args, **kwargs):
        try:
            self.dbgap_application = models.dbGaPApplication.objects.get(
                pk=kwargs["dbgap_application_pk"]
            )
        except models.dbGaPApplication.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": models.dbGaPApplication._meta.verbose_name}
            )
        if self.dbgap_application.dbgapdataaccessrequest_set.count() > 0:
            # Add a message and redirect.
            messages.error(self.request, self.ERROR_DARS_ALREADY_ADDED)
            return HttpResponseRedirect(self.dbgap_application.get_absolute_url())
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            self.dbgap_application = models.dbGaPApplication.objects.get(
                pk=kwargs["dbgap_application_pk"]
            )
        except models.dbGaPApplication.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": models.dbGaPApplication._meta.verbose_name}
            )
        if self.dbgap_application.dbgapdataaccessrequest_set.count() > 0:
            # Add a message and redirect.
            messages.error(self.request, self.ERROR_DARS_ALREADY_ADDED)
            return HttpResponseRedirect(self.dbgap_application.get_absolute_url())
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return self.dbgap_application.get_absolute_url()

    def form_valid(self, form):
        """Create the dbGaPDataAccessRequests from the json."""
        try:
            self.dbgap_application.create_dars_from_json(form.cleaned_data["json"])
        except ValueError:
            # project_id doesn't match.
            messages.error(self.request, self.ERROR_PROJECT_ID_DOES_NOT_MATCH)
            return self.form_invalid(form)
        except models.dbGaPStudyAccession.DoesNotExist:
            # At least one study accession was not found in the app.
            messages.error(self.request, self.ERROR_STUDY_ACCESSION_NOT_FOUND)
            return self.form_invalid(form)

        return super().form_valid(form)
