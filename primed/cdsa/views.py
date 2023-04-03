import django_tables2 as tables
from anvil_consortium_manager.anvil_api import AnVILAPIError
from anvil_consortium_manager.auth import (
    AnVILConsortiumManagerEditRequired,
    AnVILConsortiumManagerViewRequired,
)
from anvil_consortium_manager.models import (
    GroupAccountMembership,
    ManagedGroup,
    WorkspaceGroupSharing,
)
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.views.generic import CreateView, TemplateView

from . import forms, models


class CDSACreate(AnVILConsortiumManagerEditRequired, SuccessMessageMixin, CreateView):
    """View to create a new CDSA."""

    model = models.CDSA
    form_class = forms.CDSAForm
    success_message = "CDSA successfully created."
    ERROR_CREATING_GROUP = "Error creating Managed Group in app."

    # @transaction.atomic
    def form_valid(self, form):
        """Create a managed group in the app on AnVIL and link it to this application."""
        cc_id = form.cleaned_data["cc_id"]
        group_name = "{}_{}".format("TEST", cc_id)
        managed_group = ManagedGroup(name=group_name)
        try:
            managed_group.full_clean()
        except ValidationError:
            messages.add_message(
                self.request, messages.ERROR, self.ERROR_CREATING_GROUP
            )
            return self.render_to_response(self.get_context_data(form=form))
        try:
            managed_group.anvil_create()
        except AnVILAPIError as e:
            messages.add_message(
                self.request, messages.ERROR, "AnVIL API Error: " + str(e)
            )
            return self.render_to_response(self.get_context_data(form=form))
        managed_group.save()
        form.instance.anvil_access_group = managed_group
        return super().form_valid(form)


# Just define the tables here for now.
class PITable(tables.Table):
    representative__name = tables.Column(
        verbose_name="Representative",
        linkify=lambda record: record.representative.get_absolute_url(),
    )
    representative_role = tables.Column(verbose_name="Role")
    study_or_center = tables.Column(
        verbose_name="Study or center", orderable=False, accessor="pk"
    )

    class Meta:
        model = models.CDSA
        fields = (
            "cc_id",
            "representative__name",
            "representative_role",
            "institution",
            "study_or_center",
            "type",
            "is_component",
        )

    def render_study_or_center(self, record):
        if hasattr(record, "member"):
            value = record.member.study_site
        elif hasattr(record, "dataaffiliate"):
            value = record.dataaffiliate.study
        elif hasattr(record, "nondataaffiliate"):
            value = record.nondataaffiliate.study_or_center
        return value


class StudyTable(tables.Table):

    study = tables.Column(verbose_name="Signing group (study?)", linkify=True)
    cdsa__representative__name = tables.Column(
        verbose_name="Signing representatitve",
        linkify=lambda record: record.cdsa.representative.get_absolute_url(),
    )

    class Meta:
        model = models.DataAffiliate
        fields = (
            "study",
            "cdsa__representative__name",
        )


class AccessTable(tables.Table):

    group__cdsa__institution = tables.Column(verbose_name="Signing institution")
    group__cdsa__representative__name = tables.Column(
        verbose_name="Signing representatitve",
        linkify=lambda record: record.group.cdsa.representative.get_absolute_url(),
    )
    study_or_center = tables.Column(
        verbose_name="Signing study or center", accessor="pk", orderable=False
    )

    class Meta:
        model = GroupAccountMembership
        fields = (
            "account__user",
            "group__cdsa__institution",
            "study_or_center",
            "group__cdsa__representative__name",
        )

    def render_study_or_center(self, record):
        if hasattr(record.group.cdsa, "member"):
            value = record.group.cdsa.member.study_site
        elif hasattr(record.group.cdsa, "dataaffiliate"):
            value = record.group.cdsa.dataaffiliate.study
        elif hasattr(record.group.cdsa, "nondataaffiliate"):
            value = record.group.cdsa.nondataaffiliate.study_or_center
        else:
            return "none"
        return value


class WorkspaceTable(tables.Table):

    # group = tables.Column(verbose_name="Signing group (study?)")
    # representative__name = tables.Column(verbose_name="Signing representatitve")

    cdsa__study = tables.Column(linkify=True)
    workspace = tables.Column(linkify=True)
    data_use_permission__abbreviation = tables.Column(verbose_name="DUO permission")
    data_use_modifiers = tables.ManyToManyColumn(
        verbose_name="DUO modifiers", transform=lambda obj: obj.abbreviation
    )
    # This is hacky but it shows what we want in the table, so ok for the prototype.
    shared = tables.DateTimeColumn(accessor="created", verbose_name="Shared")

    class Meta:
        model = models.CDSAWorkspace
        fields = (
            "workspace",
            "cdsa__study",
            "cdsa",
            "data_use_permission__abbreviation",
            "data_use_modifiers",
            "data_use_limitations",
            "created",
            "shared",
        )

    def render_shared(self, record):
        try:
            wgs = record.workspace.workspacegroupsharing_set.get(
                group__name="PRIMED_ALL"
            )
            return wgs.created
        except WorkspaceGroupSharing.DoesNotExist:
            return "—"


class CDSATables(AnVILConsortiumManagerViewRequired, TemplateView):

    template_name = "cdsa/cdsa_tables.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        qs = models.CDSA.objects.all()
        context["pi_table"] = PITable(qs)
        # All accounts in CDSA groups.
        context["accounts_table"] = AccessTable(
            GroupAccountMembership.objects.filter(group__cdsa__isnull=False)
        )
        context["study_table"] = StudyTable(
            models.DataAffiliate.objects.filter(cdsa__is_component=False)
        )
        context["workspace_table"] = WorkspaceTable(models.CDSAWorkspace.objects.all())
        return context
