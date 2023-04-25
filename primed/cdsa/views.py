from anvil_consortium_manager.auth import AnVILConsortiumManagerViewRequired
from django.http import Http404
from django.views.generic import DetailView
from django_tables2 import SingleTableView

from . import models, tables


class SignedAgreementList(AnVILConsortiumManagerViewRequired, SingleTableView):
    """Display a list of SignedAgreement objects."""

    model = models.SignedAgreement
    table_class = tables.SignedAgreementTable


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
