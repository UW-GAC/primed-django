from anvil_consortium_manager.auth import AnVILConsortiumManagerViewRequired
from django.http import Http404
from django.views.generic import DetailView

from . import models


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
