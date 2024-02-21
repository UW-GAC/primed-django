import logging

import requests
from anvil_consortium_manager.anvil_api import AnVILAPIError
from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerStaffEditRequired,
    AnVILConsortiumManagerStaffViewRequired,
)
from anvil_consortium_manager.models import (
    AnVILProjectManagerAccess,
    GroupGroupMembership,
    ManagedGroup,
    Workspace,
)
from dal import autocomplete
from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.db.utils import IntegrityError
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    TemplateView,
    UpdateView,
)
from django_tables2 import SingleTableMixin, SingleTableView
from django_tables2.export.views import ExportMixin

from . import audit, forms, helpers, models, tables

logger = logging.getLogger(__name__)


class dbGaPStudyAccessionDetail(
    AnVILConsortiumManagerStaffViewRequired, SingleTableMixin, DetailView
):
    """View to show details about a `dbGaPStudyAccession`."""

    model = models.dbGaPStudyAccession
    context_table_name = "workspace_table"

    def get_object(self, queryset=None):
        queryset = self.get_queryset()
        try:
            obj = queryset.get(dbgap_phs=self.kwargs.get("dbgap_phs"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_table(self):
        return tables.dbGaPWorkspaceStaffTable(
            Workspace.objects.filter(dbgapworkspace__dbgap_study_accession=self.object),
            exclude=(
                "dbgapworkspace__dbgap_study_accession__study",
                "dbgapworkspace__dbgap_study_accession__dbgap_phs",
            ),
        )

    def get_context_data(self, **kwargs):
        """Add show_edit_links to context data."""
        context = super().get_context_data(**kwargs)
        edit_permission_codename = (
            AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
        )
        context["show_edit_links"] = self.request.user.has_perm(
            "anvil_consortium_manager." + edit_permission_codename
        )
        return context


class dbGaPStudyAccessionList(AnVILConsortiumManagerStaffViewRequired, SingleTableView):
    """View to show a list of dbGaPStudyAccession objects."""

    model = models.dbGaPStudyAccession
    table_class = tables.dbGaPStudyAccessionTable


class dbGaPStudyAccessionCreate(
    AnVILConsortiumManagerStaffEditRequired, SuccessMessageMixin, CreateView
):
    """View to create a new dbGaPStudyAccession."""

    model = models.dbGaPStudyAccession
    form_class = forms.dbGaPStudyAccessionForm
    success_message = "dbGaP study accession created successfully."
    template_name = "dbgap/dbgapstudyaccession_create.html"


class dbGaPStudyAccessionUpdate(
    AnVILConsortiumManagerStaffEditRequired, SuccessMessageMixin, UpdateView
):
    """View to update a dbGaPStudyAccession."""

    model = models.dbGaPStudyAccession
    fields = ("studies",)
    success_message = "dbGaP study accession updated successfully."
    template_name = "dbgap/dbgapstudyaccession_update.html"

    def get_object(self, queryset=None):
        queryset = self.get_queryset()
        try:
            obj = queryset.get(dbgap_phs=self.kwargs.get("dbgap_phs"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj


class dbGaPStudyAccessionAutocomplete(
    AnVILConsortiumManagerStaffViewRequired, autocomplete.Select2QuerySetView
):
    """View to provide autocompletion for dbGaPStudyAccessions."""

    def get_queryset(self):
        """Filter to dbGaPStudyAccessions matching the query."""

        qs = models.dbGaPStudyAccession.objects.order_by("dbgap_phs")

        if self.q:
            # If the string contains phs, remove it.
            # Remove leading zeros.
            phs_digits = self.q.replace("phs", "").lstrip("0")
            qs = qs.filter(dbgap_phs__icontains=phs_digits)

        return qs


class dbGaPApplicationDetail(
    AnVILConsortiumManagerStaffViewRequired, SingleTableMixin, DetailView
):
    """View to show details about a `dbGaPApplication`."""

    model = models.dbGaPApplication
    table_class = tables.dbGaPDataAccessSnapshotTable
    context_table_name = "data_access_snapshot_table"

    def get_object(self, queryset=None):
        queryset = self.get_queryset()
        try:
            obj = queryset.get(dbgap_project_id=self.kwargs.get("dbgap_project_id"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.latest_snapshot = self.get_latest_snapshot()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_latest_snapshot(self):
        try:
            return self.object.dbgapdataaccesssnapshot_set.get(is_most_recent=True)
        except models.dbGaPDataAccessSnapshot.DoesNotExist:
            return None

    def get_table_data(self):
        return models.dbGaPDataAccessSnapshot.objects.filter(
            dbgap_application=self.object
        ).order_by("-created")

    def get_context_data(self, *args, **kwargs):
        """Add to the context.

        - A flag indicating whether to display an "add dars" button.
        - A flag to indicate whether to show a table of dars.
        """
        context = super().get_context_data(*args, **kwargs)
        if self.latest_snapshot:
            context["latest_snapshot"] = self.latest_snapshot
        else:
            context["latest_snapshot"] = None
        return context


class dbGaPApplicationList(AnVILConsortiumManagerStaffViewRequired, SingleTableView):
    """View to show a list of dbGaPApplication objects."""

    model = models.dbGaPApplication
    table_class = tables.dbGaPApplicationTable


class dbGaPApplicationCreate(
    AnVILConsortiumManagerStaffEditRequired, SuccessMessageMixin, CreateView
):
    """View to create a new dbGaPApplication."""

    model = models.dbGaPApplication
    form_class = forms.dbGaPApplicationForm
    success_message = "dbGaP application successfully created."
    anvil_access_group_pattern = "PRIMED_DBGAP_ACCESS_{project_id}"
    ERROR_CREATING_GROUP = "Error creating Managed Group in app."

    def form_valid(self, form):
        """Create a managed group in the app on AnVIL and link it to this application."""
        project_id = form.cleaned_data["dbgap_project_id"]
        group_name = "{}_DBGAP_ACCESS_{}".format(
            settings.ANVIL_DATA_ACCESS_GROUP_PREFIX, project_id
        )
        managed_group = ManagedGroup(
            name=group_name, email=group_name + "@firecloud.org"
        )
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
        # Need to wrap this entire block in a transaction because we are creating multiple objects, and don't want
        # any of them to be saved if the API call fails.
        try:
            with transaction.atomic():
                managed_group.save()
                # Create the dbgap access group.
                cc_admins_group = ManagedGroup.objects.get(
                    name=settings.ANVIL_CC_ADMINS_GROUP_NAME
                )
                membership = GroupGroupMembership.objects.create(
                    parent_group=managed_group,
                    child_group=cc_admins_group,
                    role=GroupGroupMembership.ADMIN,
                )
                membership.full_clean()
                membership.anvil_create()
                membership.save()
        except AnVILAPIError as e:
            messages.add_message(
                self.request, messages.ERROR, "AnVIL API Error: " + str(e)
            )
            return self.render_to_response(self.get_context_data(form=form))
        form.instance.anvil_access_group = managed_group
        return super().form_valid(form)


class dbGaPDataAccessSnapshotCreate(
    AnVILConsortiumManagerStaffEditRequired, SuccessMessageMixin, FormView
):

    form_class = forms.dbGaPDataAccessSnapshotForm
    template_name = "dbgap/dbgapdataaccesssnapshot_form.html"
    ERROR_DARS_ALREADY_ADDED = (
        "Data Access Requests have already been added for this application."
    )
    ERROR_PROJECT_ID_DOES_NOT_MATCH = (
        "Project id in JSON does not match dbGaP application project id."
    )
    ERROR_STUDY_ACCESSION_NOT_FOUND = "Study accession(s) not found in app."
    ERROR_CREATING_DARS = "Error creating Data Access Requests."
    success_message = (
        "Successfully added Data Access Requests for this dbGaP application."
    )

    def get_dbgap_application(self):
        try:
            dbgap_application = models.dbGaPApplication.objects.get(
                dbgap_project_id=self.kwargs["dbgap_project_id"]
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
                # Update the most recent snapshot if it exists.
                try:
                    previous_snapshot = models.dbGaPDataAccessSnapshot.objects.get(
                        dbgap_application=self.dbgap_application,
                        is_most_recent=True,
                    )
                    previous_snapshot.is_most_recent = False
                    previous_snapshot.save()
                except models.dbGaPDataAccessSnapshot.DoesNotExist:
                    pass
                # Now save the new object.
                form.instance.is_most_recent = True
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


class dbGaPDataAccessSnapshotCreateMultiple(
    AnVILConsortiumManagerStaffEditRequired, SuccessMessageMixin, FormView
):

    form_class = forms.dbGaPDataAccessSnapshotMultipleForm
    template_name = "dbgap/dbgapdataaccesssnapshot_form_multiple.html"
    # ERROR_DARS_ALREADY_ADDED = (
    #     "Data Access Requests have already been added for this application."
    # )
    # ERROR_PROJECT_ID_DOES_NOT_MATCH = (
    #     "Project id in JSON does not match dbGaP application project id."
    # )
    # ERROR_STUDY_ACCESSION_NOT_FOUND = "Study accession(s) not found in app."
    ERROR_CREATING_DARS = "Error creating Data Access Requests."
    success_message = "Successfully added Data Access Requests."

    def get_context_data(self, **kwargs):
        """Add to the context data."""
        context = super().get_context_data(**kwargs)
        # The URL for updating all applications.
        project_ids = [
            x
            for x in models.dbGaPApplication.objects.values_list(
                "dbgap_project_id", flat=True
            )
        ]
        context["dbgap_dar_json_url"] = helpers.get_dbgap_dar_json_url(project_ids)
        return context

    def get_success_url(self):
        return reverse("dbgap:dbgap_applications:list")

    def form_valid(self, form):
        """Create dbGaPDataAccessSnapshots and associated dbGaPDataAccessRequests for all projects in the JSON."""
        dbgap_dar_data = form.cleaned_data["dbgap_dar_data"]
        try:
            # Use a transaction because we don't want either the snapshot or the requests
            # to be saved upon failure.
            with transaction.atomic():
                # Loop over projects.
                for project_json in dbgap_dar_data:
                    dbgap_project_id = project_json["Project_id"]
                    dbgap_application = models.dbGaPApplication.objects.get(
                        dbgap_project_id=dbgap_project_id
                    )
                    try:
                        previous_snapshot = models.dbGaPDataAccessSnapshot.objects.get(
                            dbgap_application=dbgap_application,
                            is_most_recent=True,
                        )
                        previous_snapshot.is_most_recent = False
                        previous_snapshot.save()
                    except models.dbGaPDataAccessSnapshot.DoesNotExist:
                        pass
                    # Now save the new object.
                    snapshot = models.dbGaPDataAccessSnapshot(
                        dbgap_application=dbgap_application,
                        dbgap_dar_data=project_json,
                        is_most_recent=True,
                    )
                    snapshot.full_clean()
                    snapshot.save()
                    snapshot.create_dars_from_json()
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

        # try:
        #     # Use a transaction because we don't want either the snapshot or the requests
        #     # to be saved upon failure.
        #     with transaction.atomic():
        #         # Update the most recent snapshot if it exists.
        #         try:
        #             previous_snapshot = models.dbGaPDataAccessSnapshot.objects.get(
        #                 dbgap_application=self.dbgap_application,
        #                 is_most_recent=True,
        #             )
        #             previous_snapshot.is_most_recent = False
        #             previous_snapshot.save()
        #         except models.dbGaPDataAccessSnapshot.DoesNotExist:
        #             pass
        #         # Now save the new object.
        #         form.instance.is_most_recent = True
        #         self.object = form.save()
        #         self.object.create_dars_from_json()
        # except (ValidationError, IntegrityError):
        #     # Log the JSON as an error.
        #     msg = "JSON: {}".format(form.cleaned_data["dbgap_dar_data"])
        #     logger.error(msg)
        #     # Add an error message.
        #     messages.error(self.request, self.ERROR_CREATING_DARS)
        #     return self.render_to_response(self.get_context_data(form=form))
        # except requests.exceptions.HTTPError as e:
        #     # log the error.
        #     logger.error(str(e))
        #     # Add an error message.
        #     messages.error(self.request, self.ERROR_CREATING_DARS)
        #     return self.render_to_response(self.get_context_data(form=form))
        return super().form_valid(form)


class dbGaPDataAccessSnapshotDetail(
    AnVILConsortiumManagerStaffViewRequired, DetailView
):
    """View to show details about a `dbGaPDataAccessSnapshot`."""

    model = models.dbGaPDataAccessSnapshot
    pk_url_kwarg = "dbgap_data_access_snapshot_pk"

    def get_dbgap_application(self):
        model = models.dbGaPApplication
        try:
            application = model.objects.get(
                dbgap_project_id=self.kwargs.get("dbgap_project_id")
            )
        except model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": models.dbGaPApplication._meta.verbose_name}
            )
        return application

    def get_object(self, queryset=None):
        # Get the dbGaP application using the URL parameter.
        # self.dbgap_application = self.get_dbgap_application()
        # return super().get_object(queryset=queryset)
        self.dbgap_application = self.get_dbgap_application()
        if not queryset:
            queryset = self.model.objects
        return super().get_object(
            queryset=queryset.filter(dbgap_application=self.dbgap_application)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[
            "data_access_request_table"
        ] = tables.dbGaPDataAccessRequestBySnapshotTable(
            self.object.dbgapdataaccessrequest_set.all()
        )
        context["summary_table"] = tables.dbGaPDataAccessRequestSummaryTable(
            self.object.dbgapdataaccessrequest_set.all()
            .order_by("dbgap_dac", "dbgap_current_status")
            .values("dbgap_dac", "dbgap_current_status")
            .annotate(total=Count("pk"))
        )
        return context


class dbGaPDataAccessRequestList(
    AnVILConsortiumManagerStaffViewRequired, ExportMixin, SingleTableView
):
    """View to show current DARs."""

    model = models.dbGaPDataAccessRequest
    table_class = tables.dbGaPDataAccessRequestTable
    export_name = "dars_table"

    def get_table_data(self):
        return self.get_queryset().filter(
            dbgap_data_access_snapshot__is_most_recent=True
        )


class dbGaPDataAccessRequestHistory(
    AnVILConsortiumManagerStaffViewRequired, ExportMixin, SingleTableView
):
    """View to show the history of a given DAR."""

    model = models.dbGaPDataAccessRequest
    table_class = tables.dbGaPDataAccessRequestHistoryTable
    template_name = "dbgap/dbgapdataaccessrequest_history.html"

    def get_dbgap_dar_id(self):
        return self.kwargs.get("dbgap_dar_id")

    def get(self, request, *args, **kwargs):
        self.dbgap_dar_id = self.get_dbgap_dar_id()
        return super().get(request, *args, **kwargs)

    def get_table_data(self):
        qs = self.get_queryset().filter(
            dbgap_dar_id=self.dbgap_dar_id,
        )
        if not qs.count():
            raise Http404("No DARs found matching the query.")
        return qs

    def get_table_kwargs(self):
        return {
            "order_by": "-dbgap_data_access_snapshot__created",
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dbgap_dar_id"] = self.dbgap_dar_id
        return context


class dbGaPAudit(AnVILConsortiumManagerStaffViewRequired, TemplateView):
    """View to audit access for all dbGaPApplications and dbGaPWorkspaces."""

    template_name = "dbgap/dbgap_audit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Run the audit.
        data_access_audit = audit.dbGaPAccessAudit()
        data_access_audit.run_audit()
        context["verified_table"] = data_access_audit.get_verified_table()
        context["errors_table"] = data_access_audit.get_errors_table()
        context["needs_action_table"] = data_access_audit.get_needs_action_table()
        context["data_access_audit"] = data_access_audit
        return context


class dbGaPApplicationAudit(AnVILConsortiumManagerStaffViewRequired, DetailView):
    """View to show audit results for a `dbGaPApplication`."""

    model = models.dbGaPApplication
    template_name = "dbgap/dbgapapplication_audit.html"

    def get_object(self, queryset=None):
        queryset = self.get_queryset()
        try:
            obj = queryset.get(dbgap_project_id=self.kwargs.get("dbgap_project_id"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        latest_snapshot = self.get_latest_snapshot()
        context["latest_snapshot"] = latest_snapshot
        if latest_snapshot:
            # Run the audit.
            data_access_audit = audit.dbGaPAccessAudit(
                dbgap_application_queryset=self.model.objects.filter(pk=self.object.pk)
            )
            data_access_audit.run_audit()
            context["verified_table"] = data_access_audit.get_verified_table()
            context["errors_table"] = data_access_audit.get_errors_table()
            context["needs_action_table"] = data_access_audit.get_needs_action_table()
            context["data_access_audit"] = data_access_audit
        return context


class dbGaPWorkspaceAudit(AnVILConsortiumManagerStaffViewRequired, DetailView):
    """View to show audit results for a `dbGaPWorkspace`."""

    model = models.dbGaPWorkspace
    template_name = "dbgap/dbgapworkspace_audit.html"

    def get_object(self, queryset=None):
        """Return the object the view is displaying."""

        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()
        # Filter the queryset based on kwargs.
        billing_project_slug = self.kwargs.get("billing_project_slug", None)
        workspace_slug = self.kwargs.get("workspace_slug", None)
        queryset = queryset.filter(
            workspace__billing_project__name=billing_project_slug,
            workspace__name=workspace_slug,
        )
        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(
                _("No %(verbose_name)s found matching the query")
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Run the audit.
        data_access_audit = audit.dbGaPAccessAudit(
            dbgap_workspace_queryset=self.model.objects.filter(pk=self.object.pk)
        )
        data_access_audit.run_audit()
        context["verified_table"] = data_access_audit.get_verified_table()
        context["errors_table"] = data_access_audit.get_errors_table()
        context["needs_action_table"] = data_access_audit.get_needs_action_table()
        context["data_access_audit"] = data_access_audit
        return context


class dbGaPRecordsIndex(TemplateView):
    """Index page for dbGaP records."""

    template_name = "dbgap/records_index.html"


class dbGaPApplicationRecords(SingleTableView):
    """Display a public list of dbGaP applications."""

    model = models.dbGaPApplication
    template_name = "dbgap/dbgapapplication_records.html"
    table_class = tables.dbGaPApplicationRecordsTable
