import django_tables2 as tables
from anvil_consortium_manager.models import Account, ManagedGroup, Workspace
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from . import models

User = get_user_model()


class BooleanIconColumn(tables.BooleanColumn):
    #    attrs = {"td": {"align": "center"}}
    # attrs = {"th": {"class": "center"}}

    def __init__(
        self,
        show_false_icon=False,
        true_color="green",
        false_color="red",
        true_icon="check-circle-fill",
        false_icon="x-circle-fill",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.show_false_icon = show_false_icon
        self.true_color = true_color
        self.false_color = false_color
        self.true_icon = true_icon
        self.false_icon = false_icon

    def render(self, value, record, bound_column):
        value = self._get_bool_value(record, value, bound_column)
        if value:
            rendered_value = format_html(
                """<i class="bi bi-{icon} bi-align-center px-2" style="color: {color};"></i>""",
                icon=self.true_icon,
                color=self.true_color,
            )
        else:
            if self.show_false_icon:
                rendered_value = format_html(
                    """<i class="bi bi-{icon} bi-align-center px-2" style="color: {color};"></i>""",
                    icon=self.false_icon,
                    color=self.false_color,
                )
            else:
                rendered_value = ""
        return rendered_value


class WorkspaceSharedWithConsortiumColumn(BooleanIconColumn):
    """Column that adds a check box if the workspace is shared with PRIMED_ALL."""

    def __init__(self, verbose_name="Shared with PRIMED?", orderable=False, **kwargs):
        super().__init__(verbose_name=verbose_name, orderable=orderable, **kwargs)

    def _get_bool_value(self, record, value, bound_column):
        # Check if it is a workspace
        if not isinstance(record, Workspace):
            raise ImproperlyConfigured("record must be a Workspace")
        is_shared = record.workspacegroupsharing_set.filter(group__name="PRIMED_ALL").exists()
        return is_shared


class DefaultWorkspaceUserTable(tables.Table):
    """Class to use for default workspace tables in PRIMED."""

    name = tables.Column(linkify=True, verbose_name="Workspace")
    is_shared = WorkspaceSharedWithConsortiumColumn()

    class Meta:
        model = Workspace
        fields = (
            "name",
            "is_shared",
        )
        order_by = ("name",)


class DefaultWorkspaceStaffTable(DefaultWorkspaceUserTable):
    """Class to use for default workspace tables in PRIMED."""

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
        order_by = ("short_name",)


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
        order_by = ("name",)


class DataSummaryTable(tables.Table):
    study = tables.Column()
    access_mechanism = tables.Column()
    is_shared = tables.BooleanColumn(verbose_name="Status", yesno="Shared,Preparing data")

    def __init__(self, *args, **kwargs):
        available_data_types = models.AvailableData.objects.values_list("name", flat=True)
        extra_columns = [(x, BooleanIconColumn(default=False)) for x in available_data_types]
        super().__init__(*args, extra_columns=extra_columns, **kwargs)


class UserAccountTable(tables.Table):
    """A table for `User`s with `Account` information."""

    name = tables.Column(linkify=True)
    account = tables.Column(linkify=True, verbose_name="AnVIL account")

    class Meta:
        model = User
        fields = (
            "name",
            "account",
        )
        order_by = ("name",)


class UserAccountSingleGroupMembershipTable(UserAccountTable):
    """A table with users and info about whether they are members of a group."""

    class Meta(UserAccountTable.Meta):
        pass

    is_group_member = tables.BooleanColumn(default=False)

    def __init__(self, *args, managed_group=None, **kwargs):
        if managed_group is None:
            raise ValueError("managed_group must be provided.")
        if not isinstance(managed_group, ManagedGroup):
            raise ValueError("managed_group must be an instance of ManagedGroup.")
        self.managed_group = managed_group
        super().__init__(*args, **kwargs)

    def render_is_group_member(self, record):
        if hasattr(record, "account"):
            value = record.account.groupaccountmembership_set.filter(group=self.managed_group).exists()
        else:
            value = False
        # Copied from BooleanIconColumn - maybe there is a DRYer way to do this?
        if value:
            rendered_value = mark_safe(
                """<i class="bi bi-check-circle-fill bi-align-center px-2" style="color: green;"></i>"""
            )
        else:
            rendered_value = mark_safe(
                """<i class="bi bi-x-circle-fill bi-align-center px-2" style="color: red;"></i>"""  # noqa: E501
            )
        return rendered_value
