import logging

from anvil_consortium_manager.anvil_api import AnVILAPIError
from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerEditRequired,
    AnVILConsortiumManagerViewRequired,
)
from anvil_consortium_manager.models import GroupAccountMembership, ManagedGroup
from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import inlineformset_factory
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import DetailView, FormView, TemplateView
from django_tables2 import SingleTableView

from . import forms, helpers, models, tables
from .audit import signed_agreement_audit, workspace_audit

logger = logging.getLogger(__name__)


class SignedAgreementList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """Display a list of SignedAgreement objects."""

    model = models.SignedAgreement
    table_class = tables.SignedAgreementTable


class AgreementTypeCreateMixin:
    """Mixin to for views to create specific SignedAgreement types."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "formset" not in context:
            context["formset"] = self.get_formset()
        return context

    def get_formset(self):
        """Return an instance of the MemberAgreement form to be used in this view."""
        formset_factory = inlineformset_factory(
            self.model,
            self.agreement_type_model,
            form=self.agreement_type_form_class,
            can_delete=False,
            extra=1,
            min_num=1,
            max_num=1,
        )
        formset_prefix = "agreementtype"
        if self.request.method in ("POST"):
            formset = formset_factory(
                self.request.POST,
                instance=self.object,
                prefix=formset_prefix,
                initial=[{"signed_agreement": self.object}],
            )
        else:
            formset = formset_factory(prefix=formset_prefix, initial=[{}])
        return formset

    def post(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        # Set the instance type so custom clean works as expected.
        form.instance.type = self.agreement_type_model.AGREEMENT_TYPE
        if form.is_valid():
            return self.form_valid(form)
        else:
            formset = self.get_formset()
            return self.form_invalid(form, formset)

    def get_agreement(self, form, formset):
        """Build the SignedAgreement object."""
        # Create the access group.
        access_group_name = "{}_CDSA_ACCESS_{}".format(
            settings.ANVIL_DATA_ACCESS_GROUP_PREFIX,
            form.instance.cc_id,
        )
        access_group = ManagedGroup(
            name=access_group_name, email=access_group_name + "@firecloud.org"
        )
        # Make sure the group doesn't exist already.
        access_group.full_clean()
        access_group.save()
        agreement = form.save(commit=False)
        agreement.anvil_access_group = access_group
        agreement.type = self.agreement_type_model.AGREEMENT_TYPE
        agreement.full_clean()
        return agreement

    def get_agreement_type(self, form, formset):
        """Build the agreement type object."""
        formset.forms[0].instance.signed_agreement = self.object
        agreement_type = formset.forms[0].save(commit=False)
        return agreement_type

    def anvil_create(self):
        """Create resources on ANVIL."""
        # Create AnVIL groups.
        self.object.anvil_access_group.anvil_create()

    def form_valid(self, form):
        formset = self.get_formset()
        try:
            with transaction.atomic():
                self.object = self.get_agreement(form, formset)
                self.object.save()
                if not formset.is_valid():
                    transaction.set_rollback(True)
                    return self.form_invalid(form, formset)
                # For some reason, signed_agreement isn't getting set unless I set it here.
                agreement_type = self.get_agreement_type(form, formset)
                agreement_type.save()
                self.anvil_create()
                return super().form_valid(form)
        except ValidationError as e:
            # log the error.
            logger.error(str(e))
            messages.add_message(
                self.request, messages.ERROR, self.ERROR_CREATING_GROUP
            )
            return self.render_to_response(self.get_context_data(form=form))
        except AnVILAPIError as e:
            # log the error.
            logger.error(str(e))
            messages.add_message(
                self.request, messages.ERROR, "AnVIL API Error: " + str(e)
            )
            return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form, formset):
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )

    def get_success_url(self):
        return self.object.get_absolute_url()


class MemberAgreementCreate(
    AnVILConsortiumManagerEditRequired,
    AgreementTypeCreateMixin,
    SuccessMessageMixin,
    FormView,
):
    """View to create a new MemberAgreement and corresponding SignedAgreement."""

    model = models.SignedAgreement
    form_class = forms.SignedAgreementForm
    agreement_type_model = models.MemberAgreement
    agreement_type_form_class = forms.MemberAgreementForm
    template_name = "cdsa/memberagreement_form.html"
    success_message = "Successfully created new Member Agreement."
    ERROR_CREATING_GROUP = "Error creating access group on AnVIL."


class DataAffiliateAgreementCreate(
    AnVILConsortiumManagerEditRequired,
    AgreementTypeCreateMixin,
    SuccessMessageMixin,
    FormView,
):
    """View to create a new DataAffiliateAgreement and corresponding SignedAgreement."""

    model = models.SignedAgreement
    form_class = forms.SignedAgreementForm
    agreement_type_model = models.DataAffiliateAgreement
    agreement_type_form_class = forms.DataAffiliateAgreementForm
    template_name = "cdsa/dataaffiliateagreement_form.html"
    success_message = "Successfully created new Data Affiliate Agreement."
    ERROR_CREATING_GROUP = "Error creating access or upload group."

    def anvil_create(self):
        """Create resources on ANVIL."""
        super().anvil_create()
        self.object.dataaffiliateagreement.anvil_upload_group.anvil_create()

    def get_agreement_type(self, form, formset):
        agreement_type = super().get_agreement_type(form, formset)
        # Create the upload group.
        upload_group_name = "{}_CDSA_UPLOAD_{}".format(
            settings.ANVIL_DATA_ACCESS_GROUP_PREFIX,
            form.instance.cc_id,
        )
        upload_group = ManagedGroup(
            name=upload_group_name, email=upload_group_name + "@firecloud.org"
        )
        # Make sure the group doesn't exist already.
        upload_group.full_clean()
        upload_group.save()
        agreement_type.anvil_upload_group = upload_group
        return agreement_type


class MemberAgreementDetail(AnVILConsortiumManagerViewRequired, DetailView):
    """View to show details about a `MemberAgreement`."""

    model = models.MemberAgreement

    def get_object(self, queryset=None):
        """Look up the agreement by CDSA cc_id."""
        queryset = self.get_queryset()
        try:
            obj = queryset.get(signed_agreement__cc_id=self.kwargs.get("cc_id"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj


class MemberAgreementList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """Display a list of MemberAgreement objects."""

    model = models.MemberAgreement
    table_class = tables.MemberAgreementTable


class DataAffiliateAgreementDetail(AnVILConsortiumManagerViewRequired, DetailView):
    """View to show details about a `DataAffiliateAgreement`."""

    model = models.DataAffiliateAgreement

    def get_object(self, queryset=None):
        """Look up the agreement by CDSA cc_id."""
        queryset = self.get_queryset()
        try:
            obj = queryset.get(signed_agreement__cc_id=self.kwargs.get("cc_id"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj


class DataAffiliateAgreementList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """Display a list of DataAffiliateAgreement objects."""

    model = models.DataAffiliateAgreement
    table_class = tables.DataAffiliateAgreementTable


class NonDataAffiliateAgreementCreate(
    AnVILConsortiumManagerEditRequired,
    AgreementTypeCreateMixin,
    SuccessMessageMixin,
    FormView,
):
    """View to create a new NonDataAffiliateAgreement and corresponding SignedAgreement."""

    model = models.SignedAgreement
    form_class = forms.SignedAgreementForm
    agreement_type_model = models.NonDataAffiliateAgreement
    agreement_type_form_class = forms.NonDataAffiliateAgreementForm
    template_name = "cdsa/nondataaffiliateagreement_form.html"
    success_message = "Successfully created new Non-data Affiliate Agreement."
    ERROR_CREATING_GROUP = "Error creating access group on AnVIL."


class NonDataAffiliateAgreementDetail(AnVILConsortiumManagerViewRequired, DetailView):
    """View to show details about a `NonDataAffiliateAgreement`."""

    model = models.NonDataAffiliateAgreement

    def get_object(self, queryset=None):
        """Look up the agreement by CDSA cc_id."""
        queryset = self.get_queryset()
        try:
            obj = queryset.get(signed_agreement__cc_id=self.kwargs.get("cc_id"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query"
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj


class NonDataAffiliateAgreementList(
    AnVILConsortiumManagerViewRequired, SingleTableView
):
    """Display a list of NonDataAffiliateAgreement objects."""

    model = models.NonDataAffiliateAgreement
    table_class = tables.NonDataAffiliateAgreementTable


class SignedAgreementAudit(AnVILConsortiumManagerViewRequired, TemplateView):
    """View to show audit results for `SignedAgreements`."""

    template_name = "cdsa/signedagreement_audit.html"
    ERROR_CDSA_GROUP_DOES_NOT_EXIST = (
        """The CDSA group "{}" does not exist in the app."""
    )

    def get(self, request, *args, **kwargs):
        try:
            self.audit = signed_agreement_audit.SignedAgreementAccessAudit()
        except models.ManagedGroup.DoesNotExist:
            messages.error(
                self.request,
                self.ERROR_CDSA_GROUP_DOES_NOT_EXIST.format(
                    settings.ANVIL_CDSA_GROUP_NAME
                ),
            )
            return HttpResponseRedirect(reverse("anvil_consortium_manager:index"))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Run the audit on all SignedAgreements.
        self.audit.run_audit()
        context["verified_table"] = self.audit.get_verified_table()
        context["errors_table"] = self.audit.get_errors_table()
        context["needs_action_table"] = self.audit.get_needs_action_table()
        context["audit"] = self.audit
        return context


class CDSAWorkspaceAudit(AnVILConsortiumManagerViewRequired, TemplateView):
    """View to show audit results for `CDSAWorkspaces`."""

    template_name = "cdsa/cdsaworkspace_audit.html"
    ERROR_CDSA_GROUP_DOES_NOT_EXIST = (
        """The CDSA group "{}" does not exist in the app."""
    )

    def get(self, request, *args, **kwargs):
        try:
            self.audit = workspace_audit.WorkspaceAccessAudit()
        except models.ManagedGroup.DoesNotExist:
            messages.error(
                self.request,
                self.ERROR_CDSA_GROUP_DOES_NOT_EXIST.format(
                    settings.ANVIL_CDSA_GROUP_NAME
                ),
            )
            return HttpResponseRedirect(reverse("anvil_consortium_manager:index"))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Run the audit on all SignedAgreements.
        self.audit.run_audit()
        context["verified_table"] = self.audit.get_verified_table()
        context["errors_table"] = self.audit.get_errors_table()
        context["needs_action_table"] = self.audit.get_needs_action_table()
        context["audit"] = self.audit
        return context


class RecordsIndex(TemplateView):
    """Index page for records."""

    template_name = "cdsa/records_index.html"


class RepresentativeRecords(SingleTableView):
    """Display a list of representative for required records."""

    model = models.SignedAgreement
    template_name = "cdsa/representative_records.html"

    def get_table(self):
        return helpers.get_representative_records_table()


class StudyRecords(SingleTableView):
    """Display a list of studies that have signed the CDSA for required records."""

    model = models.DataAffiliateAgreement
    template_name = "cdsa/study_records.html"

    def get_table(self):
        return helpers.get_study_records_table()


class CDSAWorkspaceRecords(SingleTableView):
    """Display a list of workspaces that contain CDSA data."""

    model = models.CDSAWorkspace
    template_name = "cdsa/cdsaworkspace_records.html"

    def get_table(self):
        return helpers.get_cdsa_workspace_records_table()


class UserAccessRecords(SingleTableView):
    """Display a list of users that have access to CDSA data via a signed CDSA."""

    model = GroupAccountMembership
    template_name = "cdsa/user_access_records.html"

    def get_table(self):
        return helpers.get_user_access_records_table()
