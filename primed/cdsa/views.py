from anvil_consortium_manager.anvil_api import AnVILAPIError
from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerEditRequired,
    AnVILConsortiumManagerViewRequired,
)
from anvil_consortium_manager.models import ManagedGroup
from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.views.generic import DetailView, FormView
from django_tables2 import SingleTableView

from . import forms, models, tables


class SignedAgreementList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """Display a list of SignedAgreement objects."""

    model = models.SignedAgreement
    table_class = tables.SignedAgreementTable


class MemberAgreementCreate(
    AnVILConsortiumManagerEditRequired, SuccessMessageMixin, FormView
):
    """View to create a new MemberAgreement and corresponding SignedAgreement."""

    model = models.SignedAgreement
    form_class = forms.SignedAgreementForm
    template_name = "cdsa/memberagreement_form.html"
    success_message = "Successfully created new Member Agreement."
    ERROR_CREATING_GROUP = "Error creating access group on AnVIL."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "formset" not in context:
            context["formset"] = self.get_formset()
        return context

    def get_formset(self):
        """Return an instance of the MemberAgreement form to be used in this view."""
        formset_factory = forms.MemberAgreementInlineFormset
        formset_prefix = "memberagreement"
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
        if form.is_valid():
            return self.form_valid(form)
        else:
            formset = self.get_formset()
            return self.form_invalid(form, formset)

        if form.is_valid() and formset.is_valid():
            print("valid")
            return self.form_valid(form, formset)
        else:
            print("invalid")
            return self.form_invalid(form, formset)

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        formset = self.get_formset()
        with transaction.atomic():
            # Create the access group.
            self.object = form.save(commit=False)
            access_group_name = "{}_CDSA_ACCESS_{}".format(
                settings.ANVIL_DATA_ACCESS_GROUP_PREFIX,
                self.object.cc_id,
            )
            access_group = ManagedGroup(name=access_group_name)
            # Make sure the group doesn't exist already.
            try:
                access_group.full_clean()
            except ValidationError:
                messages.add_message(
                    self.request, messages.ERROR, self.ERROR_CREATING_GROUP
                )
                return self.render_to_response(
                    self.get_context_data(form=form, formset=formset)
                )
            access_group.save()
            self.object.anvil_access_group = access_group
            self.object.type = self.object.MEMBER
            self.object.save()
            if not formset.is_valid():
                # import ipdb; ipdb.set_trace()
                transaction.set_rollback(True)
                return self.form_invalid(form, formset)
            # For some reason, signed_agreement isn't getting set unless I set it here.
            formset.forms[0].instance.signed_agreement = self.object
            agreement_type = formset.forms[0].save()
            #        agreement_type.signed_agreement = self.object
            agreement_type.save()
            # Create AnVIL groups.
            try:
                access_group.anvil_create()
            except AnVILAPIError as e:
                transaction.set_rollback(True)
                messages.add_message(
                    self.request, messages.ERROR, "AnVIL API Error: " + str(e)
                )
                return self.render_to_response(self.get_context_data(form=form))
            return super().form_valid(form)

    def form_invalid(self, form, formset):
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )


class DataAffiliateAgreementCreate(
    AnVILConsortiumManagerEditRequired, SuccessMessageMixin, FormView
):
    """View to create a new DataAffiliateAgreement and corresponding SignedAgreement."""

    model = models.SignedAgreement
    form_class = forms.SignedAgreementForm
    template_name = "cdsa/dataaffiliateagreement_form.html"
    success_message = "Successfully created new Data Affiliate Agreement."
    ERROR_CREATING_GROUP = "Error creating access or upload group."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "formset" not in context:
            context["formset"] = self.get_formset()
        return context

    def get_formset(self):
        """Return an instance of the DataAffiliate form to be used in this view."""
        formset_factory = forms.DataAffiliateAgreementInlineFormset
        formset_prefix = "dataaffiliateagreement"
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
        if form.is_valid():
            return self.form_valid(form)
        else:
            formset = self.get_formset()
            return self.form_invalid(form, formset)

        if form.is_valid() and formset.is_valid():
            print("valid")
            return self.form_valid(form, formset)
        else:
            print("invalid")
            return self.form_invalid(form, formset)

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        formset = self.get_formset()
        with transaction.atomic():
            # Create the access group.
            self.object = form.save(commit=False)
            access_group_name = "{}_CDSA_ACCESS_{}".format(
                settings.ANVIL_DATA_ACCESS_GROUP_PREFIX,
                self.object.cc_id,
            )
            access_group = ManagedGroup(name=access_group_name)
            # Make sure the group doesn't exist already.
            try:
                access_group.full_clean()
            except ValidationError:
                messages.add_message(
                    self.request, messages.ERROR, self.ERROR_CREATING_GROUP
                )
                return self.render_to_response(
                    self.get_context_data(form=form, formset=formset)
                )
            access_group.save()
            # Now create the upload group.
            upload_group_name = "{}_CDSA_UPLOAD_{}".format(
                settings.ANVIL_DATA_ACCESS_GROUP_PREFIX,
                self.object.cc_id,
            )
            upload_group = ManagedGroup(name=upload_group_name)
            try:
                upload_group.full_clean()
            except ValidationError:
                messages.add_message(
                    self.request, messages.ERROR, self.ERROR_CREATING_GROUP
                )
                return self.render_to_response(
                    self.get_context_data(form=form, formset=formset)
                )
            upload_group.save()
            self.object.anvil_access_group = access_group
            self.object.type = self.object.DATA_AFFILIATE
            self.object.save()
            if not formset.is_valid():
                # import ipdb; ipdb.set_trace()
                transaction.set_rollback(True)
                return self.form_invalid(form, formset)
            # For some reason, signed_agreement isn't getting set unless I set it here.
            formset.forms[0].instance.signed_agreement = self.object
            formset.forms[0].instance.anvil_upload_group = upload_group
            formset.forms[0].save()
            # Set upload group for data aaffiliate agreement.
            # Create AnVIL groups.
            try:
                access_group.anvil_create()
                upload_group.anvil_create()
            except AnVILAPIError as e:
                transaction.set_rollback(True)
                messages.add_message(
                    self.request, messages.ERROR, "AnVIL API Error: " + str(e)
                )
                return self.render_to_response(self.get_context_data(form=form))
            return super().form_valid(form)

    def form_invalid(self, form, formset):
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )


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
    AnVILConsortiumManagerEditRequired, SuccessMessageMixin, FormView
):
    """View to create a new NonDataAffiliateAgreement and corresponding SignedAgreement."""

    model = models.SignedAgreement
    form_class = forms.SignedAgreementForm
    template_name = "cdsa/nondataaffiliateagreement_form.html"
    success_message = "Successfully created new Non-data Affiliate Agreement."
    ERROR_CREATING_GROUP = "Error creating access group on AnVIL."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "formset" not in context:
            context["formset"] = self.get_formset()
        return context

    def get_formset(self):
        """Return an instance of the NonDataAffiliateAgreement form to be used in this view."""
        formset_factory = forms.NonDataAffiliateAgreementInlineFormset
        formset_prefix = "nondataaffiliateagreement"
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
        if form.is_valid():
            return self.form_valid(form)
        else:
            formset = self.get_formset()
            return self.form_invalid(form, formset)

        if form.is_valid() and formset.is_valid():
            print("valid")
            return self.form_valid(form, formset)
        else:
            print("invalid")
            return self.form_invalid(form, formset)

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        formset = self.get_formset()
        with transaction.atomic():
            # Create the access group.
            self.object = form.save(commit=False)
            access_group_name = "{}_CDSA_ACCESS_{}".format(
                settings.ANVIL_DATA_ACCESS_GROUP_PREFIX,
                self.object.cc_id,
            )
            access_group = ManagedGroup(name=access_group_name)
            # Make sure the group doesn't exist already.
            try:
                access_group.full_clean()
            except ValidationError:
                messages.add_message(
                    self.request, messages.ERROR, self.ERROR_CREATING_GROUP
                )
                return self.render_to_response(
                    self.get_context_data(form=form, formset=formset)
                )
            access_group.save()
            self.object.anvil_access_group = access_group
            self.object.type = self.object.NON_DATA_AFFILIATE
            self.object.save()
            if not formset.is_valid():
                # import ipdb; ipdb.set_trace()
                transaction.set_rollback(True)
                return self.form_invalid(form, formset)
            # For some reason, signed_agreement isn't getting set unless I set it here.
            formset.forms[0].instance.signed_agreement = self.object
            formset.forms[0].save()
            # Create AnVIL groups.
            try:
                access_group.anvil_create()
            except AnVILAPIError as e:
                transaction.set_rollback(True)
                messages.add_message(
                    self.request, messages.ERROR, "AnVIL API Error: " + str(e)
                )
                return self.render_to_response(self.get_context_data(form=form))
            return super().form_valid(form)

    def form_invalid(self, form, formset):
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )


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
