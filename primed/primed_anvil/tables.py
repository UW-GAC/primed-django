import django_tables2 as tables
from anvil_consortium_manager.models import Account

from . import models


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

    class Meta:
        model = Account
        fields = ("email", "user__name", "user__study_sites", "is_service_account")


class AvailableDataTable(tables.Table):
    """A table for the AvailableData model."""

    class Meta:
        model = models.AvailableData
        fields = ("name", "description")
