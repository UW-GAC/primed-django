from anvil_consortium_manager import ManagedGroup
from django.conf import settings
from django.db import models
from django_extensions.db.models import TimeStampedModel


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
        help_text="Study site, study, or center that the CDSA is associated with."
    )
    representatitive_role = models.CharField(
        help_text="Representative's role in the group."
    )
    anvil_access_group = models.OneToOneField(
        ManagedGroup, verbose_name=" AnVIL access group"
    )

    def clean(self):
        """Custom validation checks."""
        # To add?
        # - Dealing with component? Is this worth it? Or have a foreign key to self to the non-component?
