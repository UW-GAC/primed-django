import django_tables2 as tables
from anvil_consortium_manager.models import Account, Workspace
from django.utils.html import format_html

from . import models


class BooleanCheckColumn(tables.BooleanColumn):

    #    attrs = {"td": {"align": "center"}}
    # attrs = {"th": {"class": "center"}}

    def render(self, value, record, bound_column):
        value = self._get_bool_value(record, value, bound_column)
        if value:
            icon = "check-circle-fill"
            color = "green"
            value = format_html(
                """<i class="bi bi-{} bi-align-center px-2" style="color: {};"></i>""".format(
                    icon, color
                )
            )
        else:
            value = ""
        return value


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
        order_by = ("name",)


class StudyTable(tables.Table):
    """A table for `Study`s."""

    short_name = tables.columns.Column(linkify=True)

    class Meta:
        model = models.Study
        fields = ("short_name", "full_name")
        order_by = ("short_name",)


class StudySiteTable(tables.Table):
    """A table for `StudySite`s."""

    short_name = tables.columns.Column(linkify=True)

    class Meta:
        model = models.StudySite
        fields = ("short_name", "full_name")


class AccountTable(tables.Table):
    """A custom table for `Accounts`."""

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


class DataSummaryTable(tables.Table):

    study = tables.Column()
    access_mechanism = tables.Column()
    is_shared = tables.BooleanColumn(
        verbose_name="Status", yesno="Shared,Preparing data"
    )

    def __init__(self, *args, **kwargs):
        available_data_types = models.AvailableData.objects.values_list(
            "name", flat=True
        )
        extra_columns = [
            (x, BooleanCheckColumn(default=False)) for x in available_data_types
        ]
        super().__init__(*args, extra_columns=extra_columns, **kwargs)
