import logging

from anvil_consortium_manager.anvil_api import AnVILAPIError
from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerStaffEditRequired,
    AnVILConsortiumManagerStaffViewRequired,
    AnVILProjectManagerAccess,
)
from anvil_consortium_manager.models import (
    Account,
    GroupAccountMembership,
    GroupGroupMembership,
    ManagedGroup,
)
from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import inlineformset_factory
from django.forms.forms import Form
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, TemplateView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django_tables2 import MultiTableMixin, SingleTableMixin, SingleTableView

from primed.primed_anvil.tables import UserAccountSingleGroupMembershipTable

from . import forms, helpers, models, tables, viewmixins
from .audit import accessor_audit, signed_agreement_audit, uploader_audit, workspace_audit

logger = logging.getLogger(__name__)


class AgreementMajorVersionDetail(AnVILConsortiumManagerStaffViewRequired, MultiTableMixin, DetailView):
    """Display a "detail" page for an agreement major version (e.g., 1.x)."""

    model = models.AgreementMajorVersion
    template_name = "cdsa/agreementmajorversion_detail.html"
    tables = (tables.AgreementVersionTable, tables.SignedAgreementTable)

    def get_object(self, queryset=None):
        queryset = self.model.objects.all()
        try:
            major_version = self.kwargs["major_version"]
            obj = queryset.get(version=major_version)
        except (KeyError, self.model.DoesNotExist):
            raise Http404(
                _("No %(verbose_name)s found matching the query") % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_tables_data(self):
        agreement_version_qs = models.AgreementVersion.objects.filter(major_version=self.object)
        signed_agreement_qs = models.SignedAgreement.objects.filter(version__major_version=self.object)
        return [agreement_version_qs, signed_agreement_qs]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_deprecation_message"] = not self.object.is_valid
        edit_permission_codename = "anvil_consortium_manager." + (
            AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
        )
        context["show_invalidate_button"] = self.object.is_valid and self.request.user.has_perm(
            edit_permission_codename
        )
        return context


class AgreementMajorVersionInvalidate(AnVILConsortiumManagerStaffEditRequired, SuccessMessageMixin, UpdateView):
    """A view to invalidate an AgreementMajorVersion instance.

    This view sets the is_valid field to False. It also sets the status of all associated
    CDSAs to LAPSED.
    """

    # Note that this view mimics the DeleteView.
    model = models.AgreementMajorVersion
    # form_class = Form
    form_class = forms.AgreementMajorVersionIsValidForm
    template_name = "cdsa/agreementmajorversion_confirm_invalidate.html"
    success_message = "Successfully invalidated major agreement version."
    ERROR_ALREADY_INVALID = "This version has already been invalidated."

    def get_object(self, queryset=None):
        queryset = self.model.objects.all()
        try:
            major_version = self.kwargs["major_version"]
            obj = queryset.get(version=major_version)
        except (KeyError, self.model.DoesNotExist):
            raise Http404(
                _("No %(verbose_name)s found matching the query") % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_initial(self):
        """Set is_valid to False, since this view is invalidating a specific AgreementMajorVersion."""
        initial = super().get_initial()
        initial["is_valid"] = False
        return initial

    def get(self, response, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.is_valid:
            messages.error(self.request, self.ERROR_ALREADY_INVALID)
            return HttpResponseRedirect(self.object.get_absolute_url())
        return super().get(response, *args, **kwargs)

    def post(self, response, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.is_valid:
            messages.error(self.request, self.ERROR_ALREADY_INVALID)
            return HttpResponseRedirect(self.object.get_absolute_url())
        return super().post(response, *args, **kwargs)

    def form_valid(self, form):
        models.SignedAgreement.objects.filter(
            status=models.SignedAgreement.StatusChoices.ACTIVE,
            version__major_version=self.object,
        ).update(status=models.SignedAgreement.StatusChoices.LAPSED)
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()

    # Change status for CDSAs to lapsed when their major version is invalidated.


class AgreementVersionDetail(AnVILConsortiumManagerStaffViewRequired, SingleTableMixin, DetailView):
    """Display a "detail" page for an agreement major/minor version (e.g., 1.3)."""

    model = models.AgreementVersion
    table_class = tables.SignedAgreementTable
    context_table_name = "signed_agreement_table"

    def get_table_data(self):
        qs = models.SignedAgreement.objects.filter(version=self.object)
        # import ipdb; ipdb.set_trace()
        return qs

    def get_object(self, queryset=None):
        queryset = self.model.objects.all()
        try:
            major_version = self.kwargs["major_version"]
            minor_version = self.kwargs["minor_version"]
            obj = queryset.get(major_version__version=major_version, minor_version=minor_version)
        except (KeyError, self.model.DoesNotExist):
            raise Http404(
                _("No %(verbose_name)s found matching the query") % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_deprecation_message"] = not self.object.major_version.is_valid
        return context


class AgreementVersionList(AnVILConsortiumManagerStaffViewRequired, SingleTableView):
    """Display a list of AgreementVersions."""

    model = models.AgreementVersion
    table_class = tables.AgreementVersionTable


class SignedAgreementList(AnVILConsortiumManagerStaffViewRequired, SingleTableView):
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
        access_group = ManagedGroup(name=access_group_name, email=access_group_name + "@firecloud.org")
        # Make sure the group doesn't exist already.
        access_group.full_clean()
        access_group.save()
        # Add the cc admins group as a member.
        cc_admins_group = ManagedGroup.objects.get(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)
        self.admin_access_membership = GroupGroupMembership(
            parent_group=access_group,
            child_group=cc_admins_group,
            role=GroupGroupMembership.ADMIN,
        )
        self.admin_access_membership.full_clean()
        self.admin_access_membership.save()
        # Now finally save the agreement.
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
        self.admin_access_membership.anvil_create()

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
            messages.add_message(self.request, messages.ERROR, self.ERROR_CREATING_GROUP)
            return self.render_to_response(self.get_context_data(form=form))
        except AnVILAPIError as e:
            # log the error.
            logger.error(str(e))
            messages.add_message(self.request, messages.ERROR, "AnVIL API Error: " + str(e))
            return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form, formset):
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def get_success_url(self):
        return self.object.get_absolute_url()


class MemberAgreementCreate(
    AnVILConsortiumManagerStaffEditRequired,
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
    AnVILConsortiumManagerStaffEditRequired,
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
        self.admin_upload_membership.anvil_create()

    def get_agreement_type(self, form, formset):
        agreement_type = super().get_agreement_type(form, formset)
        # Create the upload group.
        upload_group_name = "{}_CDSA_UPLOAD_{}".format(
            settings.ANVIL_DATA_ACCESS_GROUP_PREFIX,
            form.instance.cc_id,
        )
        upload_group = ManagedGroup(name=upload_group_name, email=upload_group_name + "@firecloud.org")
        # Make sure the group doesn't exist already.
        upload_group.full_clean()
        upload_group.save()
        # Add the cc admins group as a member.
        cc_admins_group = ManagedGroup.objects.get(name=settings.ANVIL_CC_ADMINS_GROUP_NAME)
        self.admin_upload_membership = GroupGroupMembership(
            parent_group=upload_group,
            child_group=cc_admins_group,
            role=GroupGroupMembership.ADMIN,
        )
        self.admin_upload_membership.full_clean()
        self.admin_upload_membership.save()
        agreement_type.anvil_upload_group = upload_group
        return agreement_type


class MemberAgreementDetail(viewmixins.SignedAgreementViewPermissionMixin, SingleTableMixin, DetailView):
    """View to show details about a `MemberAgreement`."""

    model = models.MemberAgreement

    def get_table(self):
        return UserAccountSingleGroupMembershipTable(
            self.object.signed_agreement.accessors.all(), managed_group=self.object.signed_agreement.anvil_access_group
        )

    def get_object(self, queryset=None):
        """Look up the agreement by CDSA cc_id."""
        queryset = self.get_queryset()
        try:
            obj = queryset.get(signed_agreement__cc_id=self.kwargs.get("cc_id"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query" % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_deprecation_message"] = not self.object.signed_agreement.version.major_version.is_valid
        edit_permission_codename = "anvil_consortium_manager." + (
            AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
        )
        context["show_update_button"] = self.request.user.has_perm(edit_permission_codename)
        return context


class MemberAgreementList(AnVILConsortiumManagerStaffViewRequired, SingleTableView):
    """Display a list of MemberAgreement objects."""

    model = models.MemberAgreement
    table_class = tables.MemberAgreementTable


class SignedAgreementStatusUpdate(AnVILConsortiumManagerStaffEditRequired, SuccessMessageMixin, UpdateView):
    model = models.SignedAgreement
    form_class = forms.SignedAgreementStatusForm
    template_name = "cdsa/signedagreement_status_update.html"
    agreement_type = None
    success_message = "Successfully updated Signed Agreement status."

    def get_object(self, queryset=None):
        """Look up the agreement by agreement_type_indicator and CDSA cc_id."""
        queryset = self.get_queryset()
        if not self.kwargs.get("agreement_type"):
            raise Http404("No agreement_type provided.")
        try:
            obj = queryset.get(cc_id=self.kwargs.get("cc_id"), type=self.kwargs.get("agreement_type"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query" % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj


class SignedAgreementAccessorsUpdate(AnVILConsortiumManagerStaffEditRequired, SuccessMessageMixin, UpdateView):
    """Update accessors for a SignedAgreement object."""

    model = models.SignedAgreement
    form_class = forms.SignedAgreementAccessorsForm
    template_name = "cdsa/signedagreement_accessors_update.html"
    agreement_type = None
    success_message = "Successfully updated Signed Agreement accessors."

    def get_object(self, queryset=None):
        """Look up the agreement by agreement_type_indicator and CDSA cc_id."""
        queryset = self.get_queryset()
        if not self.kwargs.get("agreement_type"):
            raise Http404("No agreement_type provided.")
        try:
            obj = queryset.get(cc_id=self.kwargs.get("cc_id"), type=self.kwargs.get("agreement_type"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query" % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj


class DataAffiliateAgreementDetail(viewmixins.SignedAgreementViewPermissionMixin, MultiTableMixin, DetailView):
    """View to show details about a `DataAffiliateAgreement`."""

    model = models.DataAffiliateAgreement

    def get_tables(self):
        return (
            UserAccountSingleGroupMembershipTable(
                self.object.signed_agreement.accessors.all(),
                managed_group=self.object.signed_agreement.anvil_access_group,
            ),
            UserAccountSingleGroupMembershipTable(
                self.object.uploaders.all(), managed_group=self.object.anvil_upload_group
            ),
        )

    def get_object(self, queryset=None):
        """Look up the agreement by CDSA cc_id."""
        queryset = self.get_queryset()
        try:
            obj = queryset.get(signed_agreement__cc_id=self.kwargs.get("cc_id"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query" % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_deprecation_message"] = not self.object.signed_agreement.version.major_version.is_valid
        edit_permission_codename = "anvil_consortium_manager." + (
            AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
        )
        context["show_update_button"] = self.request.user.has_perm(edit_permission_codename)
        return context


class DataAffiliateAgreementList(AnVILConsortiumManagerStaffViewRequired, SingleTableView):
    """Display a list of DataAffiliateAgreement objects."""

    model = models.DataAffiliateAgreement
    table_class = tables.DataAffiliateAgreementTable


class DataAffiliateAgreementUploadersUpdate(AnVILConsortiumManagerStaffEditRequired, SuccessMessageMixin, UpdateView):
    """Update uploaders for a DataAffiliateAgreement object."""

    model = models.DataAffiliateAgreement
    form_class = forms.DataAffiliateAgreementUploadersForm
    template_name = "cdsa/dataaffiliateagreement_uploaders_update.html"
    success_message = "Successfully updated Data Affiliate Agreement uploaders."

    def get_object(self, queryset=None):
        """Look up the agreement by CDSA cc_id."""
        queryset = self.get_queryset()
        try:
            obj = queryset.get(signed_agreement__cc_id=self.kwargs.get("cc_id"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query" % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj


class NonDataAffiliateAgreementCreate(
    AnVILConsortiumManagerStaffEditRequired,
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


class NonDataAffiliateAgreementDetail(viewmixins.SignedAgreementViewPermissionMixin, SingleTableMixin, DetailView):
    """View to show details about a `NonDataAffiliateAgreement`."""

    model = models.NonDataAffiliateAgreement

    def get_table(self):
        return UserAccountSingleGroupMembershipTable(
            self.object.signed_agreement.accessors.all(), managed_group=self.object.signed_agreement.anvil_access_group
        )

    def get_object(self, queryset=None):
        """Look up the agreement by CDSA cc_id."""
        queryset = self.get_queryset()
        try:
            obj = queryset.get(signed_agreement__cc_id=self.kwargs.get("cc_id"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query" % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_deprecation_message"] = not self.object.signed_agreement.version.major_version.is_valid
        edit_permission_codename = "anvil_consortium_manager." + (
            AnVILProjectManagerAccess.STAFF_EDIT_PERMISSION_CODENAME
        )
        context["show_update_button"] = self.request.user.has_perm(edit_permission_codename)
        return context


class NonDataAffiliateAgreementList(AnVILConsortiumManagerStaffViewRequired, SingleTableView):
    """Display a list of NonDataAffiliateAgreement objects."""

    model = models.NonDataAffiliateAgreement
    table_class = tables.NonDataAffiliateAgreementTable


class SignedAgreementAudit(AnVILConsortiumManagerStaffViewRequired, TemplateView):
    """View to show audit results for `SignedAgreements`."""

    template_name = "cdsa/signedagreement_audit.html"
    ERROR_CDSA_GROUP_DOES_NOT_EXIST = """The CDSA group "{}" does not exist in the app."""

    def get(self, request, *args, **kwargs):
        if not models.ManagedGroup.objects.filter(name=settings.ANVIL_CDSA_GROUP_NAME).exists():
            messages.error(
                self.request,
                self.ERROR_CDSA_GROUP_DOES_NOT_EXIST.format(settings.ANVIL_CDSA_GROUP_NAME),
            )
            return HttpResponseRedirect(reverse("anvil_consortium_manager:index"))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        audit = signed_agreement_audit.SignedAgreementAccessAudit()
        audit.run_audit()
        context["verified_table"] = audit.get_verified_table()
        context["errors_table"] = audit.get_errors_table()
        context["needs_action_table"] = audit.get_needs_action_table()
        context["audit"] = audit
        return context


class SignedAgreementAuditResolve(AnVILConsortiumManagerStaffEditRequired, SingleObjectMixin, FormView):
    model = models.SignedAgreement
    form_class = Form
    template_name = "cdsa/signedagreement_audit_resolve.html"
    htmx_success = """<i class="bi bi-check-circle-fill"></i> Handled!"""
    htmx_error = """<i class="bi bi-x-circle-fill"></i> Error!"""

    def get_object(self, queryset=None):
        """Look up the agreement by CDSA cc_id."""
        queryset = self.get_queryset()
        try:
            obj = queryset.get(cc_id=self.kwargs.get("cc_id"))
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query" % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_audit_result(self):
        audit = signed_agreement_audit.SignedAgreementAccessAudit(
            signed_agreement_queryset=models.SignedAgreement.objects.filter(pk=self.object.pk)
        )
        audit.run_audit()
        return audit.get_all_results()[0]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.audit_result = self.get_audit_result()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.audit_result = self.get_audit_result()
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.object
        context["audit_result"] = self.audit_result
        return context

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        cdsa_group = ManagedGroup.objects.get(name=settings.ANVIL_CDSA_GROUP_NAME)
        # Handle the result.
        try:
            with transaction.atomic():
                if isinstance(self.audit_result, signed_agreement_audit.GrantAccess):
                    # Add to CDSA group.
                    membership = GroupGroupMembership(
                        parent_group=cdsa_group,
                        child_group=self.object.anvil_access_group,
                        role=GroupGroupMembership.MEMBER,
                    )
                    membership.anvil_create()
                    membership.full_clean()
                    membership.save()
                elif isinstance(self.audit_result, signed_agreement_audit.RemoveAccess):
                    # Remove from CDSA group.
                    membership = GroupGroupMembership.objects.get(
                        parent_group=cdsa_group,
                        child_group=self.object.anvil_access_group,
                    )
                    membership.anvil_delete()
                    membership.delete()
                else:
                    pass
        except AnVILAPIError as e:
            if self.request.htmx:
                return HttpResponse(self.htmx_error)
            else:
                messages.error(self.request, "AnVIL API Error: " + str(e))
                return super().form_invalid(form)
        # Otherwise, the audit resolution succeeded.
        if self.request.htmx:
            return HttpResponse(self.htmx_success)
        else:
            return super().form_valid(form)


class CDSAWorkspaceAudit(AnVILConsortiumManagerStaffViewRequired, TemplateView):
    """View to show audit results for `CDSAWorkspaces`."""

    template_name = "cdsa/cdsaworkspace_audit.html"
    ERROR_CDSA_GROUP_DOES_NOT_EXIST = """The CDSA group "{}" does not exist in the app."""

    def get(self, request, *args, **kwargs):
        try:
            self.audit = workspace_audit.WorkspaceAccessAudit()
        except models.ManagedGroup.DoesNotExist:
            messages.error(
                self.request,
                self.ERROR_CDSA_GROUP_DOES_NOT_EXIST.format(settings.ANVIL_CDSA_GROUP_NAME),
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


class CDSAWorkspaceAuditResolve(AnVILConsortiumManagerStaffEditRequired, SingleObjectMixin, FormView):
    model = models.CDSAWorkspace
    form_class = Form
    template_name = "cdsa/cdsaworkspace_audit_resolve.html"
    htmx_success = """<i class="bi bi-check-circle-fill"></i> Handled!"""
    htmx_error = """<i class="bi bi-x-circle-fill"></i> Error!"""

    def get_object(self, queryset=None):
        """Look up the agreement by CDSA workspace billing project and name."""
        queryset = self.get_queryset()
        try:
            obj = queryset.get(
                workspace__billing_project__name=self.kwargs.get("billing_project_slug"),
                workspace__name=self.kwargs.get("workspace_slug"),
            )
        except queryset.model.DoesNotExist:
            raise Http404(
                "No %(verbose_name)s found matching the query" % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_audit_result(self):
        audit = workspace_audit.WorkspaceAccessAudit(
            cdsa_workspace_queryset=models.CDSAWorkspace.objects.filter(pk=self.object.pk)
        )
        audit.run_audit()
        return audit.get_all_results()[0]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.audit_result = self.get_audit_result()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.audit_result = self.get_audit_result()
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.object
        context["audit_result"] = self.audit_result
        return context

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        cdsa_group = ManagedGroup.objects.get(name=settings.ANVIL_CDSA_GROUP_NAME)
        auth_domain = self.object.workspace.authorization_domains.first()
        # Handle the result.
        try:
            with transaction.atomic():
                if isinstance(self.audit_result, workspace_audit.GrantAccess):
                    # Add CDSA group to workspace auth domain.
                    membership = GroupGroupMembership(
                        parent_group=auth_domain,
                        child_group=cdsa_group,
                        role=GroupGroupMembership.MEMBER,
                    )
                    membership.full_clean()
                    membership.save()
                    membership.anvil_create()
                elif isinstance(self.audit_result, workspace_audit.RemoveAccess):
                    # Remove CDSA group from workspace auth domain.
                    membership = GroupGroupMembership.objects.get(
                        parent_group=auth_domain,
                        child_group=cdsa_group,
                    )
                    membership.delete()
                    membership.anvil_delete()
                else:
                    pass
        except AnVILAPIError as e:
            if self.request.htmx:
                return HttpResponse(self.htmx_error)
            else:
                messages.error(self.request, "AnVIL API Error: " + str(e))
                return super().form_invalid(form)
        # Otherwise, the audit resolution succeeded.
        if self.request.htmx:
            return HttpResponse(self.htmx_success)
        else:
            return super().form_valid(form)


class SignedAgreementAccessorAudit(AnVILConsortiumManagerStaffViewRequired, TemplateView):
    """View to show accessor audit results for `SignedAgreements`."""

    template_name = "cdsa/signedagreement_accessor_audit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        audit = accessor_audit.SignedAgreementAccessorAudit()
        audit.run_audit()
        context["verified_table"] = audit.get_verified_table()
        context["errors_table"] = audit.get_errors_table()
        context["needs_action_table"] = audit.get_needs_action_table()
        context["audit"] = audit
        return context


class SignedAgreementAccessorAuditResolve(AnVILConsortiumManagerStaffEditRequired, FormView):
    form_class = Form
    template_name = "cdsa/signedagreement_accessor_audit_resolve.html"
    htmx_success = """<i class="bi bi-check-circle-fill"></i> Handled!"""
    htmx_error = """<i class="bi bi-x-circle-fill"></i> Error!"""

    def get_signed_agreement(self):
        """Look up the SignedAgreement by cc_id."""
        try:
            obj = models.SignedAgreement.objects.get(cc_id=self.kwargs.get("cc_id"))
        except models.SignedAgreement.DoesNotExist:
            raise Http404("No SignedAgreements found matching the query")
        return obj

    def get_email(self):
        return self.kwargs.get("email")

    def get_audit_result(self):
        audit = accessor_audit.SignedAgreementAccessorAudit(
            queryset=models.SignedAgreement.objects.filter(pk=self.signed_agreement.pk)
        )
        # No way to include a queryset of members at this point - need to call the sub method directly.
        audit.audit_agreement_and_object(self.signed_agreement, self.email)
        # Set to completed, because we are just running this one specific check.
        audit.completed = True
        return audit.get_all_results()[0]

    def get(self, request, *args, **kwargs):
        self.signed_agreement = self.get_signed_agreement()
        self.email = self.get_email()
        try:
            self.audit_result = self.get_audit_result()
        except ValueError as e:
            raise Http404(str(e))
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.signed_agreement = self.get_signed_agreement()
        self.email = self.get_email()
        try:
            self.audit_result = self.get_audit_result()
        except ValueError as e:
            raise Http404(str(e))
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["signed_agreement"] = self.signed_agreement
        context["email"] = self.email
        context["audit_result"] = self.audit_result
        return context

    def get_success_url(self):
        return self.signed_agreement.get_absolute_url()

    def form_valid(self, form):
        # Add or remove the user from the access group.
        try:
            with transaction.atomic():
                if isinstance(self.audit_result, accessor_audit.GrantAccess):
                    # Only accounts should be added to the access group, so we shouldn't need to check type.
                    membership = GroupAccountMembership(
                        group=self.signed_agreement.anvil_access_group,
                        account=self.audit_result.member,
                        role=GroupAccountMembership.MEMBER,
                    )
                    membership.full_clean()
                    membership.save()
                    membership.anvil_create()
                elif isinstance(self.audit_result, accessor_audit.RemoveAccess):
                    if isinstance(self.audit_result.member, Account):
                        membership = GroupAccountMembership.objects.get(
                            group=self.signed_agreement.anvil_access_group,
                            account=self.audit_result.member,
                        )
                    elif isinstance(self.audit_result.member, ManagedGroup):
                        membership = GroupGroupMembership.objects.get(
                            parent_group=self.signed_agreement.anvil_access_group,
                            child_group=self.audit_result.member,
                        )
                    membership.delete()
                    membership.anvil_delete()
                else:
                    pass
        except AnVILAPIError as e:
            if self.request.htmx:
                return HttpResponse(self.htmx_error)
            else:
                messages.error(self.request, "AnVIL API Error: " + str(e))
                return super().form_invalid(form)
        # Otherwise, the audit resolution succeeded.
        if self.request.htmx:
            return HttpResponse(self.htmx_success)
        else:
            return super().form_valid(form)


class DataAffiliateUploaderAudit(AnVILConsortiumManagerStaffViewRequired, TemplateView):
    """View to show uploader audit results for `DataAffiliateAgreements`."""

    template_name = "cdsa/uploader_audit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        audit = uploader_audit.DataAffiliateUploaderAudit()
        audit.run_audit()
        context["verified_table"] = audit.get_verified_table()
        context["errors_table"] = audit.get_errors_table()
        context["needs_action_table"] = audit.get_needs_action_table()
        context["audit"] = audit
        return context


class DataAffiliateUploaderAuditResolve(AnVILConsortiumManagerStaffEditRequired, FormView):
    form_class = Form
    template_name = "cdsa/uploader_audit_resolve.html"
    htmx_success = """<i class="bi bi-check-circle-fill"></i> Handled!"""
    htmx_error = """<i class="bi bi-x-circle-fill"></i> Error!"""

    def get_data_affiliate_agreement(self):
        """Look up the DataAffiliateAgreement by cc_id."""
        try:
            obj = models.DataAffiliateAgreement.objects.get(signed_agreement__cc_id=self.kwargs.get("cc_id"))
        except models.DataAffiliateAgreement.DoesNotExist:
            raise Http404("No DataAffiliateAgreements found matching the query")
        return obj

    def get_email(self):
        return self.kwargs.get("email")

    def get_audit_result(self):
        audit = uploader_audit.DataAffiliateUploaderAudit(
            queryset=models.DataAffiliateAgreement.objects.filter(pk=self.data_affiliate_agreement.pk)
        )
        # No way to include a queryset of members at this point - need to call the sub method directly.
        audit.audit_agreement_and_object(self.data_affiliate_agreement, self.email)
        # Set to completed, because we are just running this one specific check.
        audit.completed = True
        return audit.get_all_results()[0]

    def get(self, request, *args, **kwargs):
        self.data_affiliate_agreement = self.get_data_affiliate_agreement()
        self.email = self.get_email()
        try:
            self.audit_result = self.get_audit_result()
        except ValueError as e:
            raise Http404(str(e))
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.data_affiliate_agreement = self.get_data_affiliate_agreement()
        self.email = self.get_email()
        try:
            self.audit_result = self.get_audit_result()
        except ValueError as e:
            raise Http404(str(e))
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["data_affiliate_agreement"] = self.data_affiliate_agreement
        context["email"] = self.email
        context["audit_result"] = self.audit_result
        return context

    def get_success_url(self):
        return self.data_affiliate_agreement.get_absolute_url()

    def form_valid(self, form):
        # Add or remove the user from the access group.
        try:
            with transaction.atomic():
                if isinstance(self.audit_result, uploader_audit.GrantAccess):
                    # Only accounts should be added to the access group, so we shouldn't need to check type.
                    membership = GroupAccountMembership(
                        group=self.data_affiliate_agreement.anvil_upload_group,
                        account=self.audit_result.member,
                        role=GroupAccountMembership.MEMBER,
                    )
                    membership.full_clean()
                    membership.save()
                    membership.anvil_create()
                elif isinstance(self.audit_result, uploader_audit.RemoveAccess):
                    if isinstance(self.audit_result.member, Account):
                        membership = GroupAccountMembership.objects.get(
                            group=self.data_affiliate_agreement.anvil_upload_group,
                            account=self.audit_result.member,
                        )
                    elif isinstance(self.audit_result.member, ManagedGroup):
                        membership = GroupGroupMembership.objects.get(
                            parent_group=self.data_affiliate_agreement.anvil_upload_group,
                            child_group=self.audit_result.member,
                        )
                    membership.delete()
                    membership.anvil_delete()
                else:
                    pass
        except AnVILAPIError as e:
            if self.request.htmx:
                return HttpResponse(self.htmx_error)
            else:
                messages.error(self.request, "AnVIL API Error: " + str(e))
                return super().form_invalid(form)
        # Otherwise, the audit resolution succeeded.
        if self.request.htmx:
            return HttpResponse(self.htmx_success)
        else:
            return super().form_valid(form)


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
