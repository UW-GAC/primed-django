import django_tables2 as tables
from anvil_consortium_manager.models import Account, Workspace
from django.utils.html import format_html

from . import models


class WorkspaceSharedWithConsortiumTable(tables.Table):
    """Table including a column to indicate if a workspace is shared with PRIMED_ALL."""

    is_shared = tables.columns.Column(
        accessor="pk",
        verbose_name="Shared with PRIMED?",
        orderable=False,
    )

    def render_is_shared(self, record):
        is_shared = record.workspacegroupsharing_set.filter(
            group__name="PRIMED_ALL"
        ).exists()
        if is_shared:
            icon = "check-circle-fill"
            color = "green"
            value = format_html(
                """<i class="bi bi-{}" style="color: {};"></i>""".format(icon, color)
            )
        else:
            value = ""
        return value


class DefaultWorkspaceTable(WorkspaceSharedWithConsortiumTable, tables.Table):
    """Class to use for default workspace tables in PRIMED."""

    name = tables.Column(linkify=True, verbose_name="Workspace")
    billing_project = tables.Column(linkify=True)
    number_groups = tables.Column(
        verbose_name="Number of groups shared with",
        empty_values=(),
        orderable=False,
        accessor="workspacegroupsharing_set__count",
    )

    class Meta:
        model = Workspace
        fields = (
            "name",
            "billing_project",
            "number_groups",
            "is_shared",
        )


class StudyTable(tables.Table):
    """A table for `Study`s."""

    short_name = tables.columns.Column(linkify=True)

    class Meta:
        model = models.Study
        fields = ("short_name", "full_name")


class StudySiteTable(tables.Table):
    """A table for `StudySite`s."""

    short_name = tables.columns.Column(linkify=True)

    class Meta:
        model = models.StudySite
        fields = ("short_name", "full_name")


class AccountTable(tables.Table):
    """A custom table for `Accounts`."""

    """Class to display a BillingProject table."""

    email = tables.Column(linkify=True)
    user__name = tables.Column(linkify=lambda record: record.user.get_absolute_url())
    is_service_account = tables.BooleanColumn(verbose_name="Service account?")
    number_groups = tables.Column(
        verbose_name="Number of groups",
        empty_values=(),
        orderable=False,
        accessor="groupaccountmembership_set__count",
    )

    class Meta:
        model = Account
        fields = ("email", "user__name", "user__study_sites", "is_service_account")


class AvailableDataTable(tables.Table):
    """A table for the AvailableData model."""

    class Meta:
        model = models.AvailableData
        fields = ("name", "description")
