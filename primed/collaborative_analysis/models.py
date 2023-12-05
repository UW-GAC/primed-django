from anvil_consortium_manager.models import BaseWorkspaceData, Workspace
from django.conf import settings
from django.db import models
from django_extensions.db.models import TimeStampedModel


# Note that "RequesterModel" is not included, because we have the "custodian" tracked instead.
class CollaborativeAnalysisWorkspace(TimeStampedModel, BaseWorkspaceData):

    purpose = models.TextField(
        help_text="The intended purpose for this workspace.",
    )
    proposal_id = models.IntegerField(
        help_text="The ID of the proposal that this workspace is associated with.",
        blank=True,
        null=True,
    )
    # Other options:
    # manager, organizer, supervisor, overseer, controller, organizer,
    # custodian, caretaker, warden,
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        help_text="The custodian for this workspace.",
    )
    source_workspaces = models.ManyToManyField(
        Workspace,
        related_name="collaborative_analysis_workspaces",
        help_text="Workspaces contributing data to this workspace.",
    )
