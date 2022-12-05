"""Tables for the `dbgap` app."""

import django_tables2 as tables
from anvil_consortium_manager.models import Workspace
from django.utils.html import format_html

from . import models


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

    def render_dbgap_phs(self, value):
        return "phs{0:06d}".format(value)


class dbGaPWorkspaceTable(tables.Table):
    """Class to render a table of Workspace objects with dbGaPWorkspace workspace data."""

    name = tables.columns.Column(linkify=True)

    class Meta:
        model = Workspace
        fields = (
            "name",
            "dbgapworkspace__dbgap_study_accession__studies",
            "dbgapworkspace__dbgap_study_accession__dbgap_phs",
            "dbgapworkspace__dbgap_version",
            "dbgapworkspace__dbgap_participant_set",
            "dbgapworkspace__dbgap_consent_abbreviation",
        )

    def render_dbgapworkspace__dbgap_phs(self, value):
        return "phs{0:06d}".format(value)

    def render_dbgapworkspace__version(self, value):
        return "v{}".format(value)


class dbGaPApplicationTable(tables.Table):
    """Class to render a table of dbGaPApplication objects."""

    dbgap_project_id = tables.columns.Column(linkify=True)
    principal_investigator = tables.columns.Column(linkify=True)
    number_approved_dars = tables.columns.Column(
        verbose_name="Number of approved DARs",
        orderable=False,
        empty_values=(False,),
        accessor="dbgapdataaccesssnapshot_set__exists",
    )
    number_requested_dars = tables.columns.Column(
        verbose_name="Number of requested DARs",
        orderable=False,
        empty_values=(False,),
        accessor="dbgapdataaccesssnapshot_set__exists",
    )
    last_update = tables.columns.DateTimeColumn(
        accessor="dbgapdataaccesssnapshot_set__exists",
        orderable=False,
        empty_values=(False,),
    )

    def render_number_approved_dars(self, value, record):
        n_dars = (
            record.dbgapdataaccesssnapshot_set.latest("created")
            .dbgapdataaccessrequest_set.approved()
            .count()
        )
        return n_dars

    def render_number_requested_dars(self, value, record):
        n_dars = record.dbgapdataaccesssnapshot_set.latest(
            "created"
        ).dbgapdataaccessrequest_set.count()
        return n_dars

    def render_last_update(self, value, record):
        return record.dbgapdataaccesssnapshot_set.latest("created").created

    class Meta:
        model = models.dbGaPApplication
        fields = (
            "dbgap_project_id",
            "principal_investigator",
        )


class dbGaPDataAccessSnapshotTable(tables.Table):
    """Class to render a table of dbGaPDataAccessSnapshot objects."""

    class Meta:
        model = models.dbGaPDataAccessSnapshot
        fields = (
            "pk",
            "created",
        )

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
        accessor="dbgapdataaccesssnapshot_set__exists",
    )

    def render_pk(self, record):
        return "See details"

    def render_number_approved_dars(self, value, record):
        n_dars = record.dbgapdataaccessrequest_set.approved().count()
        return n_dars

    def render_number_requested_dars(self, value, record):
        n_dars = record.dbgapdataaccessrequest_set.count()
        return n_dars


class dbGaPDataAccessRequestTable(tables.Table):
    """Class to render a table of dbGaPDataAccessRequest objects."""

    workspace = tables.columns.Column(
        linkify=True, accessor="get_dbgap_workspace", orderable=False
    )
    in_authorization_domain = tables.columns.Column(
        accessor="has_access",
        empty_values=(None,),
        orderable=False,
        verbose_name="In auth domain?",
    )

    def render_in_authorization_domain(self, value, record):
        if value:
            icon = "check-circle-fill"
            color = "green"
        else:
            icon = "x-square-fill"
            color = "red"
        html = format_html(
            """<i class="bi bi-{}" style="color: {};"></i>""".format(icon, color)
        )
        return html

    def render_dbgap_phs(self, value):
        return "phs{0:06d}".format(value)

    class Meta:
        model = models.dbGaPDataAccessRequest
        fields = (
            "dbgap_dar_id",
            "dbgap_dac",
            "dbgap_phs",
            "original_version",
            "original_participant_set",
            "dbgap_consent_code",
            "dbgap_consent_abbreviation",
            "dbgap_current_status",
        )


class dbGaPDataAccessRequestSummaryTable(tables.Table):
    """Table intended to show a summary of data access requests, grouped by DAC and current status."""

    dbgap_dac = tables.columns.Column(attrs={"class": "col-auto"})
    dbgap_current_status = tables.columns.Column()
    total = tables.columns.Column()

    class Meta:
        model = models.dbGaPDataAccessRequest
        fields = ("dbgap_dac", "dbgap_current_status", "total")
        attrs = {"class": "table table-sm"}
