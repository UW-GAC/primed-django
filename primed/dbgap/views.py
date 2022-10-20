import logging

import requests
from anvil_consortium_manager.anvil_api import AnVILAPIError
from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerEditRequired,
    AnVILConsortiumManagerViewRequired,
)
from anvil_consortium_manager.models import ManagedGroup, Workspace
from anvil_consortium_manager.views import SuccessMessageMixin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from django.http import Http404
from django.views.generic import CreateView, DetailView, FormView
from django_tables2 import SingleTableMixin, SingleTableView

from . import forms, models, tables

logger = logging.getLogger(__name__)


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

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.latest_snapshot = self.get_latest_snapshot()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_latest_snapshot(self):
        try:
            return self.object.dbgapdataaccesssnapshot_set.latest("created")
        except models.dbGaPDataAccessSnapshot.DoesNotExist:
            return None

    def get_table(self):
        if self.latest_snapshot:
            qs = self.latest_snapshot.dbgapdataaccessrequest_set.all()
        else:
            qs = models.dbGaPDataAccessRequest.objects.none()
        return tables.dbGaPDataAccessRequestTable(qs)

    def get_context_data(self, *args, **kwargs):
        """Add to the context.

        - A flag indicating whether to display an "add dars" button.
        - A flag to indicate whether to show a table of dars.
        """
        context = super().get_context_data(*args, **kwargs)
        if self.latest_snapshot:
            context["has_snapshot"] = True
            context["last_update"] = self.latest_snapshot.created
        else:
            context["has_snapshot"] = False
            context["last_update"] = None
        return context


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
    anvil_group_pattern = "PRIMED_DBGAP_ACCESS_{project_id}"
    ERROR_CREATING_GROUP = "Error creating Managed Group in app."

    # @transaction.atomic
    def form_valid(self, form):
        """Create a managed group in the app on AnVIL and link it to this application."""
        project_id = form.cleaned_data["project_id"]
        group_name = self.anvil_group_pattern.format(project_id=project_id)
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
        form.instance.anvil_group = managed_group
        return super().form_valid(form)


class dbGaPDataAccessSnapshotCreate(
    AnVILConsortiumManagerEditRequired, SuccessMessageMixin, FormView
):

    form_class = forms.dbGaPDataAccessJSONForm
    template_name = "dbgap/dbgapdataaccesssnapshot_form.html"
    ERROR_DARS_ALREADY_ADDED = (
        "Data Access Requests have already been added for this application."
    )
    ERROR_PROJECT_ID_DOES_NOT_MATCH = (
        "Project id in JSON does not match dbGaP application project id."
    )
    ERROR_STUDY_ACCESSION_NOT_FOUND = "Study accession(s) not found in app."
    ERROR_CREATING_DARS = "Error creating Data Access Requests."
    success_msg = "Successfully added Data Access Requests for this dbGaP application."

    def get_dbgap_application(self):
        try:
            dbgap_application = models.dbGaPApplication.objects.get(
                pk=self.kwargs["dbgap_application_pk"]
            )
        except models.dbGaPApplication.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": models.dbGaPApplication._meta.verbose_name}
            )
        return dbgap_application

    def get(self, request, *args, **kwargs):
        self.dbgap_application = self.get_dbgap_application()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.dbgap_application = self.get_dbgap_application()
        return super().post(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["dbgap_application"] = self.dbgap_application
        return initial

    def get_success_url(self):
        return self.dbgap_application.get_absolute_url()

    def form_valid(self, form):
        """Create a dbGaPDataAccessSnapshot and associated dbGaPDataAccessRequests."""
        try:
            # Use a transaction because we don't want either the snapshot or the requests
            # to be saved upon failure.
            with transaction.atomic():
                self.object = form.save()
                self.object.create_dars_from_json()
        except (ValidationError, IntegrityError):
            # Log the JSON as an error.
            msg = "JSON: {}".format(form.cleaned_data["dbgap_dar_data"])
            logger.error(msg)
            # Add an error message.
            messages.error(self.request, self.ERROR_CREATING_DARS)
            return self.render_to_response(self.get_context_data(form=form))
        except requests.exceptions.HTTPError as e:
            # log the error.
            logger.error(str(e))
            # Add an error message.
            messages.error(self.request, self.ERROR_CREATING_DARS)
            return self.render_to_response(self.get_context_data(form=form))
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        """Add the dbGaPApplication to the context data."""
        if "dbgap_application" not in kwargs:
            kwargs["dbgap_application"] = self.dbgap_application
        return super().get_context_data(*args, **kwargs)
