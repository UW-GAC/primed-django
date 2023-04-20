"""Model defintions for the `cdsa` app."""

from datetime import date

from anvil_consortium_manager.models import ManagedGroup
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from primed.primed_anvil.models import Study, StudySite


class AgreementVersion(TimeStampedModel, models.Model):
    """Model to track approved CDSA versions."""

    major_version = models.IntegerField(
        help_text="Major version of the CDSA. Changes to the major version require resigning.", validators=[MinValueValidator(1)]
    )
    minor_version = models.IntegerField(
        help_text="Minor version of the CDSA. Changes to the minor version do not require resigning.", validators=[MinValueValidator(0)]
    )
    date_approved = models.DateField(
        help_text="Date that this AgreementVersion was approved by the PRIMED Consortium.",
        default=date.today,
    )

    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["major_version", "minor_version"],
                name="unique_agreement_version",
            )
        ]
        ordering = ["major_version", "minor_version"]


# # class SignedAgreement(TimeStampedModel, models.Model):
# #     """Model to track verified, signed consortium data sharing agreements."""
# #
# #     MEMBER = "member"
# #     MEMBER_COMPONENT = "member_component"
# #     DATA_AFFILIATE = "data_affiliate"
# #     DATA_AFFILIATE_COMPONENT = "data_affiliate_component"
# #     NON_DATA_AFFILIATE = "non_data_affiliate"
# #     NON_DATA_AFFILIATE_COMPONENT = "non_data_affiliate_component"
# #     TYPE_CHOICES = (
# #         (MEMBER, "Member"),
# #         (MEMBER_COMPONENT, "Member component"),
# #         (DATA_AFFILIATE, "Data affiliate"),
# #         (DATA_AFFILIATE_COMPONENT, "Data affiliate component"),
# #         (NON_DATA_AFFILIATE, "Non-data affiliate"),
# #         (NON_DATA_AFFILIATE_COMPONENT, "Non-data affiliate component"),
# #     )
# #
# #     cc_id = models.IntegerField(
# #         help_text="Identifier assigned by the Coordinating Center.",
# #         unique=True,
# #     )
# #     representative = models.ForeignKey(
# #         settings.AUTH_USER_MODEL,
# #         on_delete=models.PROTECT,
# #         help_text="The investigator who signed this Agreement.",
# #     )
# #     representative_role = models.CharField(
# #         max_length=255,
# #         help_text="Representative's role in the group.",
# #     )
# #     # We don't have an institution model so this has to be free text.
# #     # We also don't want to link to the representative's institution, since this should *not* update
# #     # if the investigator changes institutions.
# #     institution = models.CharField(
# #         max_length=255,
# #         help_text="Signing institution for this Agreement.",
# #     )
# #     # This is needed to know which agreement type model to link to, and to validate the agreement type model itself.
# #     type = models.CharField(
# #         verbose_name="Agreement type",
# #         max_length=31,
# #         choices=TYPE_CHOICES,
# #     )
# #     version = models.ForeignKey(
# #         AgreementVersion,
# #         help_text="The version of the CDSA that was signed.",
# #         on_delete=models.PROTECT,
# #     )
# #     date_last_signed = models.DateField(
# #         help_text="Date that this Agreement was last signed.",
# #         default=date.today,
# #     )
# #     anvil_access_group = models.OneToOneField(
# #         ManagedGroup,
# #         verbose_name=" AnVIL access group",
# #         on_delete=models.PROTECT,
# #     )
# #
# #     history = HistoricalRecords()
# #
# #     def __str__(self):
# #         return "{}".format(self.cc_id)
#
#
# # class AgreementTypeModel(models.Model):
# #     """An abstract model that can be used to provide required fields for agreement type models."""
# #
# #     # This field should be set by child classes inheriting from this model.
# #     AGREEMENT_TYPE = None
# #     ERROR_TYPE_DOES_NOT_MATCH = "The type of the SignedAgreement does not match the expected type for this model."
# #
# #     signed_agreement = models.OneToOneField(
# #         SignedAgreement, on_delete=models.CASCADE, primary_key=True
# #     )
# #     history = HistoricalRecords(inherit=True)
# #
# #     class Meta:
# #         abstract = True
# #
# #     def __str__(self):
# #         return str(self.signed_agreement)
# #
# #     def clean(self):
# #         """Ensure that the SignedAgreement type is correct for the class."""
# #         if self.signed_agreement.type != self.AGREEMENT_TYPE:
# #             raise ValidationError({"signed_agreement": self.ERROR_TYPE_DOES_NOT_MATCH})
# #
# #
# # class MemberAgreement(TimeStampedModel, AgreementTypeModel, models.Model):
# #     """A model to hold additional fields for signed member CDSAs."""
# #
# #     AGREEMENT_TYPE = SignedAgreement.MEMBER
# #
# #     study_site = models.ForeignKey(
# #         StudySite,
# #         on_delete=models.CASCADE,
# #         help_text="Study Site that this agreement is associated with.",
# #     )
# #
# #
# # class MemberComponentAgreement(TimeStampedModel, AgreementTypeModel, models.Model):
# #     """A model to hold additional fields for signed member component CDSAs."""
# #
# #     AGREEMENT_TYPE = SignedAgreement.MEMBER_COMPONENT
# #
# #     component_of = models.ForeignKey(MemberAgreement, on_delete=models.CASCADE)
# #
# #
# # class DataAffiliateAgreement(TimeStampedModel, AgreementTypeModel, models.Model):
# #     """A model to hold additional fields for signed data affiliate CDSAs."""
# #
# #     AGREEMENT_TYPE = SignedAgreement.DATA_AFFILIATE
# #
# #     study = models.ForeignKey(Study, on_delete=models.PROTECT)
# #
# #
# # class DataAffiliateComponentAgreement(
# #     TimeStampedModel, AgreementTypeModel, models.Model
# # ):
# #     """A model to hold additional fields for signed data affiliate component CDSAs."""
# #
# #     AGREEMENT_TYPE = SignedAgreement.DATA_AFFILIATE_COMPONENT
# #
# #     component_of = models.ForeignKey(DataAffiliateAgreement, on_delete=models.CASCADE)
# #
# #
# # class NonDataAffiliateAgreement(TimeStampedModel, AgreementTypeModel, models.Model):
# #     """A model to hold additional fields for signed non-data affiliate CDSAs."""
# #
# #     AGREEMENT_TYPE = SignedAgreement.NON_DATA_AFFILIATE
# #
# #     affiliation = models.CharField(
# #         max_length=255, help_text="The affiliation of the person signing this CDSA."
# #     )
# #
# #
# # class NonDataAffiliateComponentAgreement(
# #     TimeStampedModel, AgreementTypeModel, models.Model
# # ):
# #     """A model to hold additional fields for signed non-data affiliate component CDSAs."""
# #
# #     AGREEMENT_TYPE = SignedAgreement.NON_DATA_AFFILIATE_COMPONENT
# #
# #     component_of = models.ForeignKey(
# #         NonDataAffiliateAgreement, on_delete=models.CASCADE
# #     )
