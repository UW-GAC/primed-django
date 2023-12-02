"""Tables for the `dbgap` app."""

import django_tables2 as tables
from anvil_consortium_manager.models import Workspace
from django.template import Context, Template
from django.utils.html import format_html

from primed.primed_anvil.tables import WorkspaceSharedWithConsortiumColumn

from . import models


class dbGaPAccessionColumn(tables.Column):
    def __init__(
        self,
        accessor="get_dbgap_accession",
        dbgap_link_accessor="get_dbgap_link",
        verbose_name="dbGaP accession",
        **kwargs
    ):
        self.dbgap_link_accessor = dbgap_link_accessor
        super().__init__(accessor=accessor, verbose_name=verbose_name, **kwargs)

    def render(self, record):
        value = tables.A(self.accessor).resolve(record)
        if self.dbgap_link_accessor:
            url = tables.A(self.dbgap_link_accessor).resolve(record)
            return format_html(
                """<a href="{}" target="_blank">{} <i class="bi bi-box-arrow-up-right"></i></a>""".format(
                    url, value
                )
            )
        else:
            return value

    def value(self, record):
        return tables.A(self.accessor).resolve(record)


class ManyToManyDateTimeColumn(tables.columns.ManyToManyColumn):
    """A django-tables2 column to render a many-to-many date time column using human-readable date time formatting."""

    def transform(self, obj):
        context = Context()
        context.update({"value": obj.created, "default": self.default})
        return Template(
            """{{ value|date:"DATETIME_FORMAT"|default:default }}"""
        ).render(context)


class dbGaPStudyAccessionTable(tables.Table):
    """Class to render a table of dbGaPStudyAccession objects."""

    dbgap_phs = tables.columns.Column(linkify=True)
    studies = tables.columns.ManyToManyColumn(linkify_item=True)
    number_workspaces = tables.Column(
        verbose_name="Number of workspaces",
        orderable=False,
        accessor="dbgapworkspace_set__count",
    )

    class Meta:
        model = models.dbGaPStudyAccession
        fields = (
            "dbgap_phs",
            "studies",
        )
        order_by = ("dbgap_phs",)

    def render_dbgap_phs(self, value):
        return "phs{0:06d}".format(value)


class dbGaPWorkspaceStaffTable(tables.Table):
    """Class to render a table of Workspace objects with dbGaPWorkspace workspace data."""

    name = tables.columns.Column(linkify=True)
    billing_project = tables.Column(linkify=True)
    dbgap_accession = dbGaPAccessionColumn(
        accessor="dbgapworkspace__get_dbgap_accession",
        dbgap_link_accessor="dbgapworkspace__get_dbgap_link",
        order_by=(
            "dbgapworkspace__dbgap_study_accession__dbgap_phs",
            "dbgapworkspace__dbgap_version",
            "dbgapworkspace__dbgap_participant_set",
        ),
    )
    dbgapworkspace__dbgap_consent_abbreviation = tables.columns.Column(
        verbose_name="Consent"
    )
    number_approved_dars = tables.columns.Column(
        accessor="pk",
        verbose_name="Approved DARs",
        orderable=False,
    )
    is_shared = WorkspaceSharedWithConsortiumColumn()

    class Meta:
        model = Workspace
        fields = (
            "name",
            "billing_project",
            "dbgap_accession",
            "dbgapworkspace__dbgap_consent_abbreviation",
            "number_approved_dars",
            "is_shared",
        )
        order_by = ("name",)

    def render_number_approved_dars(self, record):
        n = (
            record.dbgapworkspace.get_data_access_requests(most_recent=True)
            .filter(dbgap_current_status=models.dbGaPDataAccessRequest.APPROVED)
            .count()
        )
        return n


class dbGaPWorkspaceUserTable(tables.Table):
    """Class to render a table of Workspace objects with dbGaPWorkspace workspace data."""

    name = tables.columns.Column()
    billing_project = tables.Column()
    dbgap_accession = dbGaPAccessionColumn(
        accessor="dbgapworkspace__get_dbgap_accession",
        dbgap_link_accessor="dbgapworkspace__get_dbgap_link",
        order_by=(
            "dbgapworkspace__dbgap_study_accession__dbgap_phs",
            "dbgapworkspace__dbgap_version",
            "dbgapworkspace__dbgap_participant_set",
        ),
    )
    dbgapworkspace__dbgap_consent_abbreviation = tables.columns.Column(
        verbose_name="Consent"
    )
    is_shared = WorkspaceSharedWithConsortiumColumn()

    class Meta:
        model = Workspace
        fields = (
            "name",
            "billing_project",
            "dbgap_accession",
            "dbgapworkspace__dbgap_consent_abbreviation",
            "is_shared",
        )
        order_by = ("name",)


class dbGaPApplicationTable(tables.Table):
    """Class to render a table of dbGaPApplication objects."""

    dbgap_project_id = tables.columns.Column(linkify=True)
    principal_investigator = tables.columns.Column(
        verbose_name="Application PI",
        linkify=lambda record: record.principal_investigator.get_absolute_url(),
        accessor="principal_investigator__name",
    )
    principal_investigator__study_sites = tables.columns.ManyToManyColumn(
        verbose_name="Study site(s)",
    )
    number_approved_dars = tables.columns.ManyToManyColumn(
        accessor="dbgapdataaccesssnapshot_set",
        filter=lambda qs: qs.filter(is_most_recent=True),
        verbose_name="Number of approved DARs",
        transform=lambda obj: obj.dbgapdataaccessrequest_set.approved().count(),
    )
    number_requested_dars = tables.columns.ManyToManyColumn(
        accessor="dbgapdataaccesssnapshot_set",
        filter=lambda qs: qs.filter(is_most_recent=True),
        verbose_name="Number of requested DARs",
        transform=lambda obj: obj.dbgapdataaccessrequest_set.count(),
    )
    last_update = ManyToManyDateTimeColumn(
        accessor="dbgapdataaccesssnapshot_set",
        filter=lambda qs: qs.filter(is_most_recent=True),
        linkify_item=True,
    )

    class Meta:
        model = models.dbGaPApplication
        fields = (
            "dbgap_project_id",
            "principal_investigator",
        )
        order_by = ("dbgap_project_id",)


class dbGaPDataAccessSnapshotTable(tables.Table):
    """Class to render a table of dbGaPDataAccessSnapshot objects."""

    class Meta:
        model = models.dbGaPDataAccessSnapshot
        fields = (
            "pk",
            "created",
        )
        order_by = ("-created",)

    pk = tables.Column(linkify=True, verbose_name="Details", orderable=False)
    number_approved_dars = tables.columns.Column(
        verbose_name="Number of approved DARs",
        orderable=False,
        empty_values=(False,),
        accessor="dbgapdataaccessrequest_set__exists",
    )
    number_requested_dars = tables.columns.Column(
        verbose_name="Number of requested DARs",
        orderable=False,
        empty_values=(False,),
        accessor="dbgapdataaccessrequest_set__exists",
    )

    def render_pk(self, record):
        return "See details"

    def render_number_approved_dars(self, record):
        n_dars = record.dbgapdataaccessrequest_set.approved().count()
        return n_dars

    def render_number_requested_dars(self, record):
        n_dars = record.dbgapdataaccessrequest_set.count()
        return n_dars


class dbGaPDataAccessRequestTable(tables.Table):
    """Class to render a table of dbGaPDataAccessRequest objects across all applications."""

    dbgap_data_access_snapshot__dbgap_application__dbgap_project_id = tables.columns.Column(
        verbose_name=" dbGaP application",
        linkify=lambda record: record.dbgap_data_access_snapshot.dbgap_application.get_absolute_url(),
    )
    dbgap_dar_id = tables.columns.Column(verbose_name="DAR")
    dbgap_dac = tables.columns.Column(verbose_name="DAC")
    dbgap_accession = dbGaPAccessionColumn(
        accessor="get_dbgap_accession",
        verbose_name="Accession",
        order_by=(
            "dbgap_phs",
            "original_version",
            "original_participant_set",
        ),
    )
    dbgap_consent_abbreviation = tables.columns.Column(verbose_name="Consent")
    dbgap_current_status = tables.columns.Column(verbose_name="Status")
    dbgap_data_access_snapshot__created = tables.columns.DateTimeColumn(
        verbose_name="Snapshot",
        linkify=lambda record: record.dbgap_data_access_snapshot.get_absolute_url(),
    )

    class Meta:
        model = models.dbGaPDataAccessRequest
        fields = (
            "dbgap_data_access_snapshot__dbgap_application__dbgap_project_id",
            "dbgap_dar_id",
            "dbgap_dac",
            "dbgap_accession",
            "dbgap_consent_abbreviation",
            "dbgap_current_status",
            "dbgap_data_access_snapshot__created",
        )
        order_by = (
            "dbgap_data_access_snapshot__dbgap_application__dbgap_project_id",
            "dbgap_dar_id",
        )
        attrs = {"class": "table table-sm"}


class dbGaPDataAccessRequestBySnapshotTable(tables.Table):
    """Class to render a table of dbGaPDataAccessRequest objects for a specific dbGaPDataAccessSnapshot."""

    dbgap_dar_id = tables.columns.Column(verbose_name="DAR")
    dbgap_dac = tables.columns.Column(verbose_name="DAC")
    dbgap_accession = dbGaPAccessionColumn(
        accessor="get_dbgap_accession",
        verbose_name="Accession",
        order_by=(
            "dbgap_phs",
            "original_version",
            "original_participant_set",
        ),
    )
    dbgap_consent_abbreviation = tables.columns.Column(verbose_name="Consent")
    dbgap_current_status = tables.columns.Column(verbose_name="Current status")
    matching_workspaces = tables.columns.Column(
        accessor="get_dbgap_workspaces", orderable=False, default=" "
    )

    class Meta:
        model = models.dbGaPDataAccessRequest
        fields = (
            "dbgap_dar_id",
            "dbgap_dac",
            "dbgap_accession",
            "dbgap_consent_abbreviation",
            "dbgap_current_status",
        )
        order_by = ("dbgap_dar_id",)
        attrs = {"class": "table table-sm"}

    def render_matching_workspaces(self, value, record):
        template_code = """
        <i class="bi bi-{% if has_access %}check-circle-fill"
        style="color: green{% else %}x-square-fill" style="color: red{% endif %};"></i>
        <a href="{{workspace.get_absolute_url}}">{{workspace}}</a>
        """
        items = []
        for dbgap_workspace in value:
            has_access = dbgap_workspace.workspace.is_in_authorization_domain(
                record.dbgap_data_access_snapshot.dbgap_application.anvil_access_group
            )
            this_context = {
                "has_access": has_access,
                "workspace": dbgap_workspace.workspace.name,
            }
            this = Template(template_code).render(Context(this_context))
            items = items + [this]
        html = format_html("" + "<br>".join(items))
        return html


class dbGaPDataAccessRequestSummaryTable(tables.Table):
    """Table intended to show a summary of data access requests, grouped by DAC and current status."""

    dbgap_dac = tables.columns.Column(attrs={"class": "col-auto"})
    dbgap_current_status = tables.columns.Column()
    total = tables.columns.Column()

    class Meta:
        model = models.dbGaPDataAccessRequest
        fields = ("dbgap_dac", "dbgap_current_status", "total")
        attrs = {"class": "table table-sm"}


class dbGaPApplicationRecordsTable(tables.Table):
    """Class to render a publicly-viewable table of dbGaPApplication objects."""

    dbgap_project_id = tables.columns.Column()
    principal_investigator = tables.columns.Column(
        verbose_name="Application PI",
        accessor="principal_investigator__name",
    )
    principal_investigator__study_sites = tables.columns.ManyToManyColumn(
        verbose_name="Study site(s)",
    )
    number_approved_dars = tables.columns.ManyToManyColumn(
        accessor="dbgapdataaccesssnapshot_set",
        filter=lambda qs: qs.filter(is_most_recent=True),
        verbose_name="Number of approved DARs",
        transform=lambda obj: obj.dbgapdataaccessrequest_set.approved().count(),
    )
    number_requested_dars = tables.columns.ManyToManyColumn(
        accessor="dbgapdataaccesssnapshot_set",
        filter=lambda qs: qs.filter(is_most_recent=True),
        verbose_name="Number of requested DARs",
        transform=lambda obj: obj.dbgapdataaccessrequest_set.count(),
    )
    last_update = ManyToManyDateTimeColumn(
        accessor="dbgapdataaccesssnapshot_set",
        filter=lambda qs: qs.filter(is_most_recent=True),
    )

    class Meta:
        model = models.dbGaPApplication
        fields = (
            "dbgap_project_id",
            "principal_investigator",
        )
        order_by = ("dbgap_project_id",)
