"""Model defintions for the `cdsa` app."""

from datetime import date

from anvil_consortium_manager.models import ManagedGroup
from django.conf import settings
from django.db import models
from django_extensions.db.models import TimeStampedModel
from simple_history.models import HistoricalRecords


class SignedAgreement(TimeStampedModel, models.Model):
    """Model to track verified, signed consortium data sharing agreements."""

    MEMBER = "member"
    MEMBER_COMPONENT = "member_component"
    DATA_AFFILIATE = "data_affiliate"
    DATA_AFFILIATE_COMPONENT = "data_affiliate_component"
    NON_DATA_AFFILIATE = "non_data_affiliate"
    NON_DATA_AFFILIATE_COMPONENT = "non_data_affiliate_component"
    TYPE_CHOICES = (
        (MEMBER, "Member"),
        (MEMBER_COMPONENT, "Member component"),
        (DATA_AFFILIATE, "Data affiliate"),
        (DATA_AFFILIATE_COMPONENT, "Data affiliate component"),
        (NON_DATA_AFFILIATE, "Non-data affiliate"),
        (NON_DATA_AFFILIATE_COMPONENT, "Non-data affiliate component"),
    )

    cc_id = models.IntegerField(
        help_text="Identifier assigned by the Coordinating Center.",
        unique=True,
    )
    representative = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        help_text="The investigator who signed this Agreement.",
    )
    representative_role = models.CharField(
        max_length=255,
        help_text="Representative's role in the group.",
    )
    # We don't have an institution model so this has to be free text.
    # We also don't want to link to the representative's institution, since this should *not* update
    # if the investigator changes institutions.
    institution = models.CharField(
        max_length=255,
        help_text="Signing institution for this Agreement.",
    )
    type = models.CharField(
        verbose_name="Agreement type",
        max_length=31,
        choices=TYPE_CHOICES,
    )
    version = models.IntegerField(
        help_text="Version of the CDSA that was signed.",
        default=1,
    )
    date_last_signed = models.DateField(
        help_text="Date that this Agreement was last signed.",
        default=date.today,
    )
    anvil_access_group = models.OneToOneField(
        ManagedGroup,
        verbose_name=" AnVIL access group",
        on_delete=models.PROTECT,
    )

    history = HistoricalRecords()

    def __str__(self):
        return "{}".format(self.cc_id)
