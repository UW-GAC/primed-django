from anvil_consortium_manager.models import BaseWorkspaceData, ManagedGroup
from django.conf import settings
from django.db import models
from django_extensions.db.models import TimeStampedModel

from primed.duo.models import DataUseOntologyModel
from primed.primed_anvil.models import AvailableData, RequesterModel, Study, StudySite


# Consider splitting this into separate models for different CDSA types.
class CDSA(TimeStampedModel, models.Model):
    """A model to track verified CDSAs."""

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
        help_text="Identifier assigned by the CC.",
        unique=True,
    )
    representative = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        help_text="The investigator who signed this CDSA.",
    )
    # We don't have an institution model so this has to be free text.
    institution = models.CharField(
        max_length=255, help_text="Signing institution for the CDSA."
    )
    type = models.CharField(
        verbose_name="CDSA type",
        max_length=31,
        choices=TYPE_CHOICES,
    )
    representative_role = models.CharField(
        max_length=255, help_text="Representative's role in the group."
    )
    anvil_access_group = models.OneToOneField(
        ManagedGroup,
        verbose_name=" AnVIL access group",
        on_delete=models.PROTECT,
    )

    def __str__(self):
        return "{}".format(self.cc_id)

    def clean(self):
        """Custom validation checks."""
        # TODO:
        # - Dealing with component? Is this worth it? Or have a foreign key to self to the non-component?


class Member(models.Model):
    cdsa = models.OneToOneField(CDSA, on_delete=models.PROTECT, primary_key=True)
    study_site = models.ForeignKey(StudySite, on_delete=models.PROTECT)

    def __str__(self):
        return str(self.cdsa)


class MemberComponent(models.Model):
    cdsa = models.OneToOneField(CDSA, on_delete=models.PROTECT, primary_key=True)
    component_of = models.ForeignKey(Member, on_delete=models.PROTECT)

    def __str__(self):
        return str(self.cdsa)


class DataAffiliate(models.Model):

    cdsa = models.OneToOneField(CDSA, on_delete=models.PROTECT, primary_key=True)
    study = models.ForeignKey(Study, on_delete=models.PROTECT)

    def __str__(self):
        return str(self.cdsa)


class DataAffiliateComponent(models.Model):
    cdsa = models.OneToOneField(CDSA, on_delete=models.PROTECT, primary_key=True)
    component_of = models.ForeignKey(DataAffiliate, on_delete=models.PROTECT)

    def __str__(self):
        return str(self.cdsa)


class NonDataAffiliate(models.Model):
    cdsa = models.OneToOneField(CDSA, on_delete=models.PROTECT, primary_key=True)
    study_or_center = models.CharField(max_length=255)

    def __str__(self):
        return str(self.cdsa)


class NonDataAffiliateComponent(models.Model):
    cdsa = models.OneToOneField(CDSA, on_delete=models.PROTECT, primary_key=True)
    component_of = models.ForeignKey(NonDataAffiliate, on_delete=models.PROTECT)

    def __str__(self):
        return str(self.cdsa)


class CDSAWorkspace(
    RequesterModel, DataUseOntologyModel, TimeStampedModel, BaseWorkspaceData
):
    """Custom workspace data model to hold information about CDSA workspaces."""

    cdsa = models.ForeignKey(DataAffiliate, on_delete=models.PROTECT)

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
