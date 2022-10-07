"""Tables for the `dbgap` app."""

import django_tables2 as tables
from anvil_consortium_manager.models import Workspace

from . import models


class dbGaPStudyAccessionTable(tables.Table):
    """A table for dbGaPStudyAccession objects."""

    phs = tables.columns.Column(linkify=True)
    study = tables.columns.Column(linkify=True)
    number_workspaces = tables.Column(
        verbose_name="Number of workspaces",
        orderable=False,
        accessor="dbgapworkspace_set__count",
    )

    class Meta:
        model = models.dbGaPStudyAccession
        fields = (
            "phs",
            "study",
        )

    def render_phs(self, value):
        return "phs{0:06d}".format(value)


class dbGaPWorkspaceTable(tables.Table):
    """A table for Workspaces that includes fields from dbGaPWorkspace."""

    name = tables.columns.Column(linkify=True)

    class Meta:
        model = Workspace
        fields = (
            "name",
            "dbgapworkspace__dbgap_study_accession__study",
            "dbgapworkspace__dbgap_study_accession__phs",
            "dbgapworkspace__dbgap_version",
            "dbgapworkspace__dbgap_participant_set",
            "dbgapworkspace__dbgap_consent_abbreviation",
        )

    def render_dbgapworkspace__phs(self, value):
        return "phs{0:06d}".format(value)

    def render_dbgapworkspace__version(self, value):
        return "v{}".format(value)


class dbGaPApplicationTable(tables.Table):
    """A table for dbGaPStudyAccession objects."""

    project_id = tables.columns.Column(linkify=True)
    principal_investigator = tables.columns.Column(linkify=True)
    number_approved_dars = tables.columns.Column(
        verbose_name="Number of approved DARs", orderable=False, empty_values=()
    )

    def render_number_approved_dars(self, value, record):
        return record.dbgapdataaccessrequest_set.approved().count()

    class Meta:
        model = models.dbGaPApplication
        fields = (
            "project_id",
            "principal_investigator",
        )


class dbGaPDataAccessRequestTable(tables.Table):

    dbgap_study_accession = tables.columns.Column(linkify=True)

    class Meta:
        model = models.dbGaPDataAccessRequest
        fields = (
            "dbgap_dar_id",
            "dbgap_study_accession",
            "dbgap_version",
            "dbgap_participant_set",
            "dbgap_consent_code",
            "dbgap_consent_abbreviation",
            "dbgap_current_status",
        )
