import json

from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerStaffEditRequired,
    AnVILConsortiumManagerStaffViewRequired,
    AnVILConsortiumManagerViewRequired,
)
from anvil_consortium_manager.models import Account, AnVILProjectManagerAccess, Workspace
from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.views.generic import CreateView, DetailView, TemplateView
from django_filters.views import FilterView
from django_tables2 import MultiTableMixin, SingleTableMixin, SingleTableView

from primed.cdsa.models import DataAffiliateAgreement, MemberAgreement
from primed.cdsa.tables import (
    CDSAWorkspaceStaffTable,
    CDSAWorkspaceUserTable,
    DataAffiliateAgreementTable,
    MemberAgreementTable,
)
from primed.dbgap.models import dbGaPApplication
from primed.dbgap.tables import (
    dbGaPApplicationTable,
    dbGaPWorkspaceStaffTable,
    dbGaPWorkspaceUserTable,
)
from primed.miscellaneous_workspaces.tables import (
    OpenAccessWorkspaceStaffTable,
    OpenAccessWorkspaceUserTable,
)
from primed.users.tables import UserTable

from . import filters, helpers, models, tables

User = get_user_model()


class StudyDetail(AnVILConsortiumManagerViewRequired, MultiTableMixin, DetailView):
    """View to show details about a `Study`."""

    model = models.Study
    tables = [
        dbGaPWorkspaceStaffTable,
        CDSAWorkspaceStaffTable,
        DataAffiliateAgreementTable,
        OpenAccessWorkspaceStaffTable,
    ]
    # table_class = dbGaPWorkspaceStaffTable
    # context_table_name = "dbgap_workspace_table"

    def get_tables(self):
        dbgap_qs = Workspace.objects.filter(dbgapworkspace__dbgap_study_accession__studies=self.object)
        cdsa_qs = Workspace.objects.filter(cdsaworkspace__study=self.object)
        agreement_qs = DataAffiliateAgreement.objects.filter(study=self.object)
        open_access_qs = Workspace.objects.filter(openaccessworkspace__studies=self.object)
        # Check permissions to determine table type.
        apm_content_type = ContentType.objects.get_for_model(AnVILProjectManagerAccess)
        full_view_perm = f"{apm_content_type.app_label}.{AnVILProjectManagerAccess.STAFF_VIEW_PERMISSION_CODENAME}"
        if self.request.user.has_perm(full_view_perm):
            return (
                dbGaPWorkspaceStaffTable(dbgap_qs),
                CDSAWorkspaceStaffTable(cdsa_qs),
                DataAffiliateAgreementTable(agreement_qs),
                OpenAccessWorkspaceStaffTable(open_access_qs),
            )
        else:
            # Assume they have limited view due to auth mixin.
            return (
                dbGaPWorkspaceUserTable(dbgap_qs),
                CDSAWorkspaceUserTable(cdsa_qs),
                DataAffiliateAgreementTable(agreement_qs),
                OpenAccessWorkspaceUserTable(open_access_qs),
            )


class StudyList(AnVILConsortiumManagerViewRequired, SingleTableView, FilterView, autocomplete.Select2QuerySetView):
    """View to show a list of `Study`s."""

    model = models.Study
    table_class = tables.StudyTable
    template_name = "primed_anvil/study_list.html"

    filterset_class = filters.StudyListFilter
    queryset = models.Study.objects.order_by("short_name")


class StudyCreate(AnVILConsortiumManagerStaffEditRequired, SuccessMessageMixin, CreateView):
    """View to create a new `Study`."""

    model = models.Study
    fields = ("short_name", "full_name")
    success_message = "Study successfully created."

    def get_success_url(self):
        return self.object.get_absolute_url()


class StudyAutocomplete(AnVILConsortiumManagerStaffViewRequired, autocomplete.Select2QuerySetView):
    """View to provide autocompletion for `Study`s. Match either the `short_name` or `full_name`."""

    def get_result_label(self, result):
        s = "{} ({})".format(result.full_name, result.short_name)
        return s

    def get_selected_result_label(self, result):
        return str(result)

    def get_queryset(self):
        # Only active accounts.
        qs = models.Study.objects.order_by("short_name")

        if self.q:
            qs = qs.filter(Q(short_name__icontains=self.q) | Q(full_name__icontains=self.q))

        return qs


class StudySiteDetail(AnVILConsortiumManagerStaffViewRequired, MultiTableMixin, DetailView):
    """View to show details about a `StudySite`."""

    model = models.StudySite

    def get_tables(self):
        user_qs = User.objects.filter(study_sites=self.object)
        dbgap_qs = dbGaPApplication.objects.filter(principal_investigator__study_sites=self.object)
        cdsa_qs = MemberAgreement.objects.filter(study_site=self.object)
        if self.object.member_group:
            account_qs = Account.objects.filter(groupaccountmembership__group=self.object.member_group)
        else:
            account_qs = Account.objects.none()
        return [
            UserTable(user_qs),
            dbGaPApplicationTable(dbgap_qs),
            MemberAgreementTable(cdsa_qs),
            tables.AccountTable(account_qs, exclude=("number_groups",)),
        ]


class StudySiteList(AnVILConsortiumManagerStaffViewRequired, SingleTableView):
    """View to show a list of `StudySite`s."""

    model = models.StudySite
    table_class = tables.StudySiteTable


class AvailableDataList(AnVILConsortiumManagerStaffViewRequired, SingleTableView):
    """View to show a list of `AvailableData`."""

    model = models.AvailableData
    table_class = tables.AvailableDataTable


class AvailableDataDetail(AnVILConsortiumManagerStaffViewRequired, SingleTableMixin, DetailView):
    """View to show details about a `AvailableData`."""

    model = models.AvailableData
    context_table_name = "dbgap_workspace_table"
    table_class = dbGaPWorkspaceStaffTable
    context_table_name = "dbgap_workspace_table"

    def get_table_data(self):
        return Workspace.objects.filter(dbgapworkspace__available_data=self.object)


class DataSummaryView(LoginRequiredMixin, TemplateView):
    template_name = "primed_anvil/data_summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table_data = helpers.get_summary_table_data()
        context["summary_table"] = tables.DataSummaryTable(table_data)
        return context


class PhenotypeInventoryInputsView(AnVILConsortiumManagerStaffViewRequired, TemplateView):
    template_name = "primed_anvil/phenotype_inventory_inputs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["workspaces_input"] = json.dumps(helpers.get_workspaces_for_phenotype_inventory(), indent=2)
        return context
