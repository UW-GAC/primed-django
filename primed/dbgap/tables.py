"""Tables for the `dbgap` app."""

import django_tables2 as tables
from anvil_consortium_manager.models import Workspace

from . import models


class dbGaPStudyTable(tables.Table):
    """A table for dbGaPStudy objects."""

    study = tables.columns.Column(linkify=True)
    number_workspaces = tables.Column(
        verbose_name="Number of workspaces",
        orderable=False,
        accessor="dbgapworkspace_set__count",
    )

    class Meta:
        model = models.dbGaPStudy
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
            "dbgapworkspace__dbgap_study__study",
            "dbgapworkspace__dbgap_study__phs",
            "dbgapworkspace__dbgap_version",
            "dbgapworkspace__dbgap_participant_set",
            "dbgapworkspace__full_consent_code",
        )

    def render_dbgapworkspace__phs(self, value):
        return "phs{0:06d}".format(value)

    def render_dbgapworkspace__version(self, value):
        return "v{}".format(value)
