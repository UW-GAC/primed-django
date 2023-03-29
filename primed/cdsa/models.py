from anvil_consortium_manager.models import BaseWorkspaceData, ManagedGroup
from django.conf import settings
from django.db import models
from django_extensions.db.models import TimeStampedModel

from primed.duo.models import DataUseOntologyModel
from primed.primed_anvil.models import AvailableData, RequesterModel, Study


# Consider splitting this into separate models for different CDSA types.
class CDSA(TimeStampedModel, models.Model):
    """A model to track verified CDSAs."""

    MEMBER = "member"
    DATA_AFFILIATE = "data_affiliate"
    NON_DATA_AFFILIATE = "non_data_affiliate"
    TYPE_CHOICES = (
        (MEMBER, "Member"),
        (DATA_AFFILIATE, "Data affiliate"),
        (NON_DATA_AFFILIATE, "Non-data affiliate"),
    )

    cc_id = models.IntegerField(
        help_text="Identifier assigned by the CC.",
        unique=True,
    )
    representative = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        help_text="The investigator who signed this CDSA.",
    )
    # We don't have an institution model so this has to be free text.
    instutition = models.CharField(max_length=255)
    type = models.CharField(
        verbose_name="CDSA type",
        max_length=31,
        choices=TYPE_CHOICES,
    )
    is_component = models.BooleanField()
    # TODO: This is ambiguously named.
    group = models.CharField(
        max_length=255,
        help_text="Study site, study, or center that the CDSA is associated with.",
    )
    representatitive_role = models.CharField(
        max_length=255, help_text="Representative's role in the group."
    )
    anvil_access_group = models.OneToOneField(
        ManagedGroup,
        verbose_name=" AnVIL access group",
        on_delete=models.PROTECT,
    )

    def clean(self):
        """Custom validation checks."""
        # TODO:
        # - Dealing with component? Is this worth it? Or have a foreign key to self to the non-component?


class CDSAWorkspace(
    RequesterModel, DataUseOntologyModel, TimeStampedModel, BaseWorkspaceData
):
    """Custom workspace data model to hold information about CDSA workspaces."""

    cdsa = models.ForeignKey(CDSA, on_delete=models.PROTECT)
    study = models.ForeignKey(Study, on_delete=models.PROTECT)

    data_use_limitations = models.TextField()
    acknowledgments = models.TextField()
    available_data = models.ManyToManyField(
        AvailableData,
        help_text="Data available in this accession.",
        blank=True,
    )

    def clean(self):
        """Custom validation checks."""
        # TODO:
        # - verify that cdsa is a data affiliate or data affiliate component.
