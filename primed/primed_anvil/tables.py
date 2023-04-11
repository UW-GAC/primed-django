import django_tables2 as tables
from anvil_consortium_manager.models import Account
from django.utils.html import format_html

from . import models


class BooleanCheckColumn(tables.BooleanColumn):

    #    attrs = {"td": {"align": "center"}}
    attrs = {"th": {"align": "center"}}

    def render(self, value, record, bound_column):
        value = self._get_bool_value(record, value, bound_column)
        if value:
            icon = "check-circle-fill"
            color = "green"
            value = format_html(
                """<i class="bi bi-{} bi-align-center" style="color: {};"></i>""".format(
                    icon, color
                )
            )
        else:
            value = ""
        return value


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
